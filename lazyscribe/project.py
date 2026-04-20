"""Project storing and logging."""

from __future__ import annotations

import copy
import getpass
import json
import logging
import warnings
from bisect import insort
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Literal, TypedDict
from urllib.parse import urlparse

import fsspec
from fsspec.spec import AbstractFileSystem
from slugify import slugify

from lazyscribe.artifacts import _get_handler
from lazyscribe.artifacts.base import Artifact
from lazyscribe.exception import ReadOnlyError, SaveError
from lazyscribe.experiment import Experiment, ReadOnlyExperiment
from lazyscribe.registry import registry
from lazyscribe.test import ReadOnlyTest, Test

LOG = logging.getLogger(__name__)


class ProjectState(TypedDict):
    """Project serialization state."""

    author: str
    experiments: list[Experiment]
    fpath: Path
    mode: Literal["r", "a", "w", "w+"]
    protocol: str
    storage_options: dict[str, Any]


def _write_artifact(
    artifact: Artifact,
    path: Path,
    fs: AbstractFileSystem,
    label: str = "",
) -> None:
    """Write a single dirty artifact to the filesystem and reset its dirty flag.

    Parameters
    ----------
    artifact : lazyscribe.artifacts.base.Artifact
        The artifact to write.
    path : pathlib.Path
        The directory path for the artifact file.
    fs : fsspec.spec.AbstractFileSystem
        The filesystem to use for writing.
    label : str, optional (default "")
        A label prefix for error messages (e.g. "test").

    Raises
    ------
    lazyscribe.exception.SaveError
        If writing the artifact to the filesystem fails.
    """
    fmode = "wb" if artifact.binary else "w"
    fpath = path / artifact.fname
    label_str = f"{label} " if label else ""
    try:
        fs.makedirs(str(path), exist_ok=True)
        with fs.open(str(fpath), fmode) as buf:
            artifact.write(artifact.value, buf, **artifact.writer_kwargs)
    except Exception as exc:
        raise SaveError(
            f"Unable to write {label_str}artifact '{artifact.name}' to '{fpath!s}'"
        ) from exc
    artifact.dirty = False
    if artifact.output_only:
        warnings.warn(
            f"Artifact '{artifact.name}' is added. It is not meant to be read back as Python Object",
            UserWarning,
            stacklevel=2,
        )


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
        self.experiments = []
        self.fs = fsspec.filesystem(self.protocol, **storage_options)

        if mode not in ("r", "a", "w", "w+"):
            raise ValueError("Please provide a valid ``mode`` value.")
        self.mode = mode
        if mode in ("r", "a", "w+") and self.fs.isfile(str(self.fpath)):
            self.load()

        self.author = getpass.getuser() if author is None else author
        self.mutex_ = Lock()

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
                for test_data in testlist:
                    test_artifacts: list[Artifact] = []
                    if "artifacts" in test_data:
                        for artifact in test_data.pop("artifacts"):
                            handler_cls = _get_handler(artifact.pop("handler"))
                            created_at = datetime.fromisoformat(
                                artifact.pop("created_at")
                            )
                            test_artifacts.append(
                                handler_cls.construct(
                                    **artifact, created_at=created_at, dirty=False
                                )
                            )
                    # exp["slug"] is still present (only "tests"/"artifacts"/"dependencies" are popped)
                    test_path = (
                        self.fpath.parent / exp["slug"] / slugify(test_data["name"])
                    )
                    if self.mode in ("r", "a"):
                        tests.append(
                            ReadOnlyTest(
                                **test_data,
                                artifacts=test_artifacts,
                                path=test_path,
                                fs=self.fs,
                            )
                        )
                    else:
                        tests.append(
                            Test(
                                **test_data,
                                artifacts=test_artifacts,
                                path=test_path,
                                fs=self.fs,
                            )
                        )

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
                insort(
                    self.experiments,
                    ReadOnlyExperiment(
                        **exp,
                        project=self.fpath,
                        fs=self.fs,
                        dependencies=dependencies,
                        tests=tests,
                        artifacts=artifacts,
                        dirty=False,
                    ),
                )
            else:
                insort(
                    self.experiments,
                    Experiment(
                        **exp,
                        project=self.fpath,
                        fs=self.fs,
                        dependencies=dependencies,
                        tests=tests,
                        artifacts=artifacts,
                        dirty=False,
                    ),
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
                has_dirty_test_artifacts = any(
                    artifact.dirty for test in exp.tests for artifact in test.artifacts
                )
                if not exp.dirty and not has_dirty_test_artifacts:
                    LOG.debug(f"{exp.slug} has not been updated. Skipping...")
                    continue
                # Write the experiment-level artifact data
                LOG.info(f"Saving artifacts for {exp.slug}")
                for artifact in exp.artifacts:
                    if not artifact.dirty:
                        LOG.debug(f"Artifact '{artifact.name}' has not been updated")
                        continue
                    LOG.debug(
                        f"Saving '{artifact.name}' to {exp.path / artifact.fname!s}..."
                    )
                    _write_artifact(artifact, exp.path, self.fs)

                # Write test-level artifact data
                for test in exp.tests:
                    for artifact in test.artifacts:
                        if not artifact.dirty:
                            LOG.debug(
                                f"Test artifact '{artifact.name}' has not been updated"
                            )
                            continue
                        LOG.debug(
                            f"Saving test artifact '{artifact.name}' to {test.path / artifact.fname!s}..."
                        )
                        _write_artifact(artifact, test.path, self.fs, label="test")

                if exp.dirty:
                    exp.dirty = False

    def merge(self, *others: Project, other: Project | None = None) -> Project:
        """Merge multiple projects.

        The new project will inherit the current project ``fpath``,
        ``author``, and ``mode``.

        For details on the merging process, see :ref:`here <Project Updating>`.

        Parameters
        ----------
        others : Project
            The projects to merge back to the original.
        other : Project, optional (default None)
            .. deprecated:: 2.2

                This argument has been deprecated to support multiple projects
                merging.

            A single other project to merge back to the original.

        Returns
        -------
        lazyscribe.project.Project
            A new project.
        """
        other_projects_ = list(others)
        if other is not None:
            warnings.warn(
                (
                    "Named argument ``other`` is deprecated and will be removed in "
                    "version 3.0. Please use a positional argument"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            other_projects_.append(other)
        cexp = copy.copy(self.experiments)
        for proj in other_projects_:
            for exp in proj.experiments:
                if exp in cexp:
                    continue
                insort(cexp, exp)
        slugs: list[str] = [exp.slug for exp in cexp]
        cexp = [
            val for idx, val in enumerate(cexp) if val.slug not in slugs[(idx + 1) :]
        ]

        new = Project(
            fpath=self.fpath,
            mode=self.mode,
            author=self.author,
            **self.storage_options,
        )
        new.experiments = cexp

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
        with self.mutex_:
            insort(self.experiments, other)

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

    def __getstate__(self) -> ProjectState:
        """Serialize the project.

        This function is useful when we want to serialize :py:class:`lazyscribe.project.Project`
        for the purposes of multiprocessing.
        """
        return {
            "author": self.author,
            "experiments": self.experiments,
            "fpath": self.fpath,
            "mode": self.mode,
            "protocol": self.protocol,
            "storage_options": self.storage_options,
        }

    def __setstate__(self, state: ProjectState) -> None:
        """Deserialize the project.

        All we need to do is assign attributes and re-instate the filesystem.
        """
        self.mutex_ = Lock()
        for key, value in state.items():
            setattr(self, key, value)
        # Re-create the filesystem
        self.fs = fsspec.filesystem(self.protocol, **self.storage_options)

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
