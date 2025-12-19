"""Project storing and logging."""

from __future__ import annotations

import getpass
import json
import logging
import warnings
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import fsspec

from lazyscribe.artifacts import _get_handler
from lazyscribe.artifacts.base import Artifact
from lazyscribe.exception import ReadOnlyError, SaveError
from lazyscribe.experiment import Experiment, ReadOnlyExperiment
from lazyscribe.linked import LinkedList, merge
from lazyscribe.registry import registry
from lazyscribe.test import ReadOnlyTest, Test

LOG = logging.getLogger(__name__)


class Project:
    """Project class.

    Parameters
    ----------
    fpath : str | pathlib.Path, optional (default "project.json")
        The location of the project file. If no project file exists, this will be the location
        of the output JSON file when ``save`` is called.
    mode : {"r", "a", "w", "w+"}, optional (default "a")
        The mode for opening the project.

        * ``r``: All existing experiments will be loaded as
          :py:class:`lazyscribe.experiment.ReadOnlyExperiment`. No new experiments can be added.
        * ``a``: All existing experiments will be loaded as
          :py:class:`lazyscribe.experiment.ReadOnlyExperiment`. New experiments can be added.
        * ``w``: No existing experiments will be loaded.
        * ``w+``: All experiments will be loaded in editable mode as
          :py:class:`lazyscribe.experiment.Experiment`. Experiments can be added.
    author : str, optional (default None)
        The project author. This author will be used for any new experiments or modifications to
        existing experiments. If not supplied, ``getpass.getuser()`` will be used.
    **storage_options
        Storage options to pass to the filesystem initialization. Will be passed to
        :py:meth:`fsspec.filesystem`.

    Attributes
    ----------
    experiments : list[lazyscribe.experiment.Experiment]
        The list of experiments in the project.

    Raises
    ------
    ValueError
        Raised on invalid ``mode`` value.
    """

    fpath: Path
    mode: Literal["r", "a", "w", "w+"]
    author: str
    storage_options: dict[str, Any]
    experiments: list[Experiment]

    def __init__(
        self,
        fpath: str | Path = "project.json",
        mode: Literal["r", "a", "w", "w+"] = "a",
        author: str | None = None,
        **storage_options: Any,
    ) -> None:
        """Init method."""
        if isinstance(fpath, str):
            parsed = urlparse(fpath)
            self.fpath = Path(parsed.netloc + parsed.path)
            self.protocol = parsed.scheme or "file"
        else:
            self.fpath = fpath
            self.protocol = "file"
        self.storage_options = storage_options

        # If in ``r``, ``a``, or ``w+`` mode, read in the existing project.
        self.experiments: list[Experiment] = []
        self.fs = fsspec.filesystem(self.protocol, **storage_options)

        if mode not in ("r", "a", "w", "w+"):
            raise ValueError("Please provide a valid ``mode`` value.")
        self.mode = mode
        if mode in ("r", "a", "w+") and self.fs.isfile(str(self.fpath)):
            self.load()

        self.author = getpass.getuser() if author is None else author

    def load(self) -> None:
        """Load existing experiments.

        If the project is in read-only or append mode, existing experiments will
        be loaded in read-only mode. If opened in editable mode, existing experiments
        will be loaded in editable mode.
        """
        with self.fs.open(str(self.fpath), "r") as infile:
            data = json.load(infile)
        for idx, entry in enumerate(data):
            data[idx]["created_at"] = datetime.fromisoformat(entry["created_at"])
            data[idx]["last_updated"] = datetime.fromisoformat(entry["last_updated"])

        upstream_projects: dict[str, Project] = {}
        for exp in data:
            dependencies: dict[str, Experiment] = {}
            if "dependencies" in exp:
                deplist = exp.pop("dependencies")
                for dep in deplist:
                    project_name, exp_name = dep.split("|")
                    if project_name in registry:
                        # The upstream experiment refers to the project registry by key
                        project = registry[project_name]
                    elif (project_key_ := registry.search(project_name)) is not None:
                        # The upstream experiment refers to a project path that has been
                        # loaded into the registry
                        project = registry[project_key_]
                    elif project_name in upstream_projects:
                        project = upstream_projects[project_name]
                    else:
                        project = Project(
                            fpath=f"{self.protocol}://{project_name}",
                            mode="r",
                            author=None,
                            **self.storage_options,
                        )
                        project.load()
                        upstream_projects[project_name] = project
                    depexp = project[exp_name]
                    dependencies[depexp.short_slug] = depexp

            tests: list[Test] = []
            if "tests" in exp:
                testlist = exp.pop("tests")
                for test in testlist:
                    if self.mode in ("r", "a"):
                        tests.append(ReadOnlyTest(**test))
                    else:
                        tests.append(Test(**test))

            artifacts: list[Artifact] = []
            if "artifacts" in exp:
                artifactlist = exp.pop("artifacts")
                for artifact in artifactlist:
                    handler_cls = _get_handler(artifact.pop("handler"))
                    created_at = datetime.fromisoformat(artifact.pop("created_at"))
                    artifacts.append(
                        handler_cls.construct(
                            **artifact, created_at=created_at, dirty=False
                        )
                    )

            if self.mode in ("r", "a"):
                self.experiments.append(
                    ReadOnlyExperiment(
                        **exp,
                        project=self.fpath,
                        fs=self.fs,
                        dependencies=dependencies,
                        tests=tests,
                        artifacts=artifacts,
                        dirty=False,
                    )
                )
            else:
                self.experiments.append(
                    Experiment(
                        **exp,
                        project=self.fpath,
                        fs=self.fs,
                        dependencies=dependencies,
                        tests=tests,
                        artifacts=artifacts,
                        dirty=False,
                    )
                )

    def save(self) -> None:
        """Save the project data.

        This includes saving any artifact data.

        Raises
        ------
        lazyscribe.exception.ReadOnlyError
            Raised when trying to save when the project is in read-only mode.
        lazyscribe.exception.SaveError
            Raised when writing to the filesystem fails.
        """
        if self.mode == "r":
            raise ReadOnlyError("Project is in read-only mode.")
        elif self.mode == "w+":
            for exp in self.experiments:
                if exp.dirty:
                    exp.last_updated_by = self.author

        data = list(self)
        with self.fs.transaction:
            try:
                self.fs.makedirs(str(self.fpath.parent), exist_ok=True)
                with self.fs.open(str(self.fpath), "w") as outfile:
                    json.dump(data, outfile, sort_keys=True, indent=4)
            except Exception as exc:
                raise SaveError(
                    f"Unable to save the Project JSON file to {self.fpath!s}"
                ) from exc

            mutable_: list[Experiment] = [
                exp
                for exp in self.experiments
                if not isinstance(exp, ReadOnlyExperiment)
            ]
            for exp in mutable_:
                if not exp.dirty:
                    LOG.debug(f"{exp.slug} has not been updated. Skipping...")
                    continue
                # Write the artifact data
                LOG.info(f"Saving artifacts for {exp.slug}")
                for artifact in exp.artifacts:
                    fmode = "wb" if artifact.binary else "w"
                    fpath = exp.path / artifact.fname
                    if not artifact.dirty:
                        LOG.debug(f"Artifact '{artifact.name}' has not been updated")
                        continue

                    try:
                        self.fs.makedirs(str(exp.path), exist_ok=True)
                        LOG.debug(f"Saving '{artifact.name}' to {fpath!s}...")
                        with self.fs.open(str(fpath), fmode) as buf:
                            artifact.write(
                                artifact.value, buf, **artifact.writer_kwargs
                            )
                    except Exception as exc:
                        raise SaveError(
                            f"Unable to write '{artifact.name}' to '{fpath!s}'"
                        ) from exc

                    # Reset the `dirty` flag since we have the updated artifact on disk
                    artifact.dirty = False
                    if artifact.output_only:
                        warnings.warn(
                            f"Artifact '{artifact.name}' is added. It is not meant to be read back as Python Object",
                            UserWarning,
                            stacklevel=2,
                        )

                exp.dirty = False

    def merge(self, other: Project) -> Project:
        """Merge two projects.

        The new project will inherit the current project ``fpath``,
        ``author``, and ``mode``.

        For details on the merging process, see :ref:`here <Project Updating>`.

        Returns
        -------
        lazyscribe.project.Project
            A new project.
        """
        # Create linked lists of experiments
        cexp = LinkedList.from_list(self.experiments)
        oexp = LinkedList.from_list(other.experiments)
        # Get the merged list of experiments
        merged = merge(cexp.head, oexp.head).to_list()  # type: ignore[arg-type]
        # De-dupe the merged list based on slug
        slugs: list[str] = [exp.slug for exp in merged]

        new = Project(
            fpath=self.fpath,
            mode=self.mode,
            author=self.author,
            **self.storage_options,
        )
        new.experiments = [
            val for idx, val in enumerate(merged) if val.slug not in slugs[idx + 1 :]
        ]

        return new

    def append(self, other: Experiment) -> None:
        """Append an experiment to the project.

        For details on the merging process, see :ref:`here <Project Appending>`.

        Parameters
        ----------
        other : lazyscribe.experiment.Experiment
            The experiment to add.

        Raises
        ------
        lazyscribe.exception.ReadOnlyError
            Raised when trying to log a new experiment when the project is in
            read-only mode.
        """
        if self.mode == "r":
            raise ReadOnlyError("Project is in read-only mode.")
        self.experiments.append(other)

    @contextmanager
    def log(self, name: str) -> Iterator[Experiment]:
        """Log an experiment to the project.

        Parameters
        ----------
        name : str
            The name of the experiment.

        Yields
        ------
        lazyscribe.experiment.Experiment
            A new :py:class:`lazyscribe.experiment.Experiment` object.

        Raises
        ------
        lazyscribe.exception.ReadOnlyError
            Raised when trying to log a new experiment when the project is in
            read-only mode.
        """
        if self.mode == "r":
            raise ReadOnlyError("Project is in read-only mode.")
        experiment = Experiment(
            name=name, project=self.fpath, fs=self.fs, author=self.author, dirty=True
        )

        yield experiment

        self.append(experiment)

    def filter(self, func: Callable[[Experiment], bool]) -> Iterator[Experiment]:
        """Filter the experiments in the project.

        Parameters
        ----------
        func : Callable[[lazyscribe.experiment.Experiment], bool]
            A callable that takes in a :py:class:`lazyscribe.experiment.Experiment` object
            and returns a boolean indicating whether or not it passes the filter.

        Yields
        ------
        lazyscribe.experiment.Experiment
            An experiment.
        """
        for exp in self.experiments:
            if func(exp):
                yield exp

    def __contains__(self, item: str) -> bool:
        """Check if the project contains an experiment with the given slug or short slug.

        Parameters
        ----------
        item : str
            The slug or short slug for the experiment.

        Returns
        -------
        bool
            Whether the item exists.
        """
        for exp in self.experiments:
            if exp.slug == item or exp.short_slug == item:
                out = True
                break
        else:
            out = False

        return out

    def __getitem__(self, arg: str) -> Experiment:
        """Use brackets to retrieve an experiment by slug.

        Parameters
        ----------
        arg : str
            The slug or short slug for the experiment.

            .. note::

                If you have multiple experiments with the same short slug, this notation
                will retrieve the first one added to the project.

        Raises
        ------
        KeyError
            Raised if the slug does not exist.
        """
        for exp in self.experiments[
            ::-1
        ]:  # reverse list to get the latest saved experiment
            if exp.slug == arg or exp.short_slug == arg:
                out = exp
                break
        else:
            raise KeyError(f"No experiment with slug {arg}")

        # If short slug is used, return the latest experiment saved with that slug, but may not correspond to the latest "last_updated" timestamp if it was manually set.
        short_slug_timestamp: list[datetime] = [
            exp.last_updated for exp in self.experiments if exp.short_slug == arg
        ]
        if len(short_slug_timestamp) > 0:
            latest_datetime = max(short_slug_timestamp)
            if out.last_updated != latest_datetime:
                LOG.warning(
                    f"Returning experiment last saved, with ``last_updated`` manually set as {exp.last_updated}. \
                            The latest ``last_updated`` timestamp is {latest_datetime}."
                )

        return out

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate through each experiment and return the dictionary.

        Yields
        ------
        dict[str, Any]
            An experiment dict.
        """
        for exp in self.experiments:
            yield exp.to_dict()
