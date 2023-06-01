"""Project storing and logging."""

from __future__ import annotations

import getpass
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import urlparse

import fsspec

from .artifacts import _get_handler
from .experiment import Experiment, ReadOnlyExperiment
from .linked import LinkedList, merge
from .test import ReadOnlyTest, Test

LOG = logging.getLogger(__name__)


class Project:
    """Project class.

    Parameters
    ----------
    fpath : str, optional (default "project.json")
        The location of the project file. If no project file exists, this will be the location
        of the output JSON file when ``save`` is called.
    mode : {"r", "a", "w", "w+"}, optional (default "w")
        The mode for opening the project.

        * ``r``: All existing experiments will be loaded as
          :py:class:`lazyscribe.experiment.ReadOnlyExperiment` and no new experiments can be logged.
        * ``a``: All existing experiments will be loaded as
          :py:class:`lazyscribe.experiment.ReadOnlyExperiment` and new experiments can be added.
        * ``w``: No existing experiments will be loaded.
        * ``w+``: All experiments will be loaded in editable mode as
          :py:class:`lazyscribe.experiment.Experiment`.
    author : str, optional (default None)
        The project author. This author will be used for any new experiments or modifications to
        existing experiments. If not supplied, ``getpass.getuser()`` will be used.
    storage_options : Dict, optional (default None)
        Storage options to pass to the filesystem initialization. Will be passed to
        fsspec.filesystem.

    Attributes
    ----------
    experiments : list
        The list of experiments in the project.
    snapshot : dict
        A on-load snapshot of the experiments and their last update timestamp. If the last updated
        timestamp has shifted when ``save`` is called, the ``last_updated_by`` field will be
        adjusted.
    """

    def __init__(
        self,
        fpath: Union[str, Path] = "project.json",
        mode: str = "w",
        author: Optional[str] = None,
        **storage_options,
    ):
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
        self.experiments: List[Union[Experiment, ReadOnlyExperiment]] = []
        self.snapshot: Dict = {}
        self.fs = fsspec.filesystem(self.protocol, **storage_options)
        self.mode = mode
        if mode in ("r", "a", "w+") and self.fs.isfile(self.fpath):
            self.load()

        self.author = getpass.getuser() if author is None else author

    def load(self):
        """Load existing experiments.

        If the project is in read-only or append mode, existing experiments will
        be loaded in read-only mode. If opened in editable mode, existing experiments
        will be loaded in editable mode.
        """
        with self.fs.open(self.fpath, "r") as infile:
            data = json.load(infile)
        for idx, entry in enumerate(data):
            data[idx]["created_at"] = datetime.fromisoformat(entry["created_at"])
            data[idx]["last_updated"] = datetime.fromisoformat(entry["last_updated"])

        parent = self.fpath.parent
        upstream_projects = {}
        for exp in data:
            dependencies = {}
            if "dependencies" in exp:
                deplist = exp.pop("dependencies")
                for dep in deplist:
                    project_name, exp_name = dep.split("|")
                    project = upstream_projects.get(project_name)
                    if not project:
                        project = Project(
                            fpath=parent / project_name,
                            mode="r",
                            **self.storage_options,
                        )
                        project.load()
                        upstream_projects[project_name] = project
                    depexp = project[exp_name]
                    dependencies[depexp.short_slug] = depexp

            tests = []
            if "tests" in exp:
                testlist = exp.pop("tests")
                for test in testlist:
                    if self.mode in ("r", "a"):
                        tests.append(ReadOnlyTest(**test))
                    else:
                        tests.append(Test(**test))

            artifacts = []
            if "artifacts" in exp:
                artifactlist = exp.pop("artifacts")
                for artifact in artifactlist:
                    handler_cls = _get_handler(artifact.pop("handler"))
                    created_at = datetime.fromisoformat(artifact.pop("created_at"))
                    artifacts.append(
                        handler_cls.construct(**artifact, created_at=created_at)
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
                    )
                )
            self.snapshot[self.experiments[-1].slug] = self.experiments[-1].last_updated

    def save(self):
        """Save the project data.

        This includes saving any artifact data.
        """
        if self.mode == "r":
            raise RuntimeError("Project is in read-only mode.")
        elif self.mode == "w+":
            for slug, last_updated in self.snapshot.items():
                if slug not in self:
                    continue
                if self[slug].last_updated > last_updated:
                    self[slug].last_updated_by = self.author

        data = list(self)
        with self.fs.open(self.fpath, "w") as outfile:
            json.dump(data, outfile, sort_keys=True, indent=4)

        for exp in self.experiments:
            if isinstance(exp, ReadOnlyExperiment):
                LOG.debug(f"{exp.slug} was opened in read-only mode. Skipping...")
                continue
            if (
                exp.slug in self.snapshot
                and exp.last_updated == self.snapshot[exp.slug]
            ):
                LOG.debug(f"{exp.slug} has not been updated. Skipping...")
                continue
            # Write the artifact data
            LOG.info(f"Saving artifacts for {exp.slug}")
            for artifact in exp.artifacts:
                fmode = "wb" if artifact.binary else "w"
                fpath = exp.dir / exp.path / artifact.fname
                if self.fs.isfile(
                    fpath
                ) and artifact.created_at <= datetime.fromtimestamp(
                    self.fs.info(fpath)["created"]
                ):
                    LOG.debug(
                        f"Artifact '{artifact.name}' already exists and has not been updated"
                    )
                    continue

                self.fs.makedirs(exp.dir / exp.path, exist_ok=True)
                LOG.debug(f"Saving '{artifact.name}' to {str(fpath)}...")
                with self.fs.open(fpath, fmode) as buf:
                    artifact.write(artifact.value, buf, **artifact.writer_kwargs)

    def merge(self, other: Project) -> Project:
        """Merge two projects.

        The new project will inherit the current project ``fpath``,
        ``author``, and ``mode``.

        Returns
        -------
        Project
            A new project.
        """
        # Create linked lists of experiments
        cexp = LinkedList.from_list(self.experiments)
        oexp = LinkedList.from_list(other.experiments)
        # Get the merged list of experiments
        merged = merge(cexp.head, oexp.head).to_list()
        # De-dupe the merged list based on slug
        slugs = [exp.slug for exp in merged]

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

    def append(self, other: Experiment):
        """Append an experiment to the project.

        Parameters
        ----------
        other : Experiment
            The experiment to add.

        Raises
        ------
        RuntimeError
            Raised when trying to log a new experiment when the project is in
            read-only mode.
        """
        if self.mode == "r":
            raise RuntimeError("Project is in read-only mode.")
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
        Experiment
            A new ``Experiment`` data class.

        Raises
        ------
        RuntimeError
            Raised when trying to log a new experiment when the project is in
            read-only mode.
        """
        if self.mode == "r":
            raise RuntimeError("Project is in read-only mode.")
        experiment = Experiment(
            name=name, project=self.fpath, fs=self.fs, author=self.author
        )

        try:
            yield experiment

            self.append(experiment)
        except Exception as exc:
            raise exc

    def to_tabular(self) -> Tuple[List, List]:
        """Create a dictionary that can be fed into ``pandas``.

        This method depends on the user consistently logging
        the same metrics and parameters to each experiment in the
        project.

        Returns
        -------
        List
            A global project list, with one entry per experiment. Each dictionary
            will have the following keys:

            +--------------------------+-------------------------------+
            | Field                    | Description                   |
            |                          |                               |
            +==========================+===============================+
            | ``("name",)``            | Name of the experiment        |
            +--------------------------+-------------------------------+
            | ``("short_slug",)``      | Short slug for the experiment |
            +--------------------------+-------------------------------+
            | ``("slug",)``            | Full slug for the experiment  |
            +--------------------------+-------------------------------+
            | ``("author",)``          | Experiment author             |
            +--------------------------+-------------------------------+
            | ``("last_updated_by",)`` | Last author                   |
            +--------------------------+-------------------------------+
            | ``("created_at",)``      | Created timestamp             |
            +--------------------------+-------------------------------+
            | ``("last_updated",)``    | Last update timestammp        |
            +--------------------------+-------------------------------+

            as well as one key per metric in the ``metrics`` dictionary
            for each experiment, with the format ``("metrics", <metric_name>)``.
        List
            A ``tests`` level list. Each entry will represent a test, with the
            following keys:

            +--------------------------+-------------------------------+
            | Field                    | Description                   |
            |                          |                               |
            +==========================+===============================+
            | ``("name",)``            | Name of the experiment        |
            +--------------------------+-------------------------------+
            | ``("short_slug",)``      | Short slug for the experiment |
            +--------------------------+-------------------------------+
            | ``("slug",)``            | Full slug for the experiment  |
            +--------------------------+-------------------------------+
            | ``("test",)``            | Test name                     |
            +--------------------------+-------------------------------+
            | ``("description",)``     | Test description              |
            +--------------------------+-------------------------------+

            as well as one key per metric in the ``metrics`` dictionary for each
            test, with the format ``("metrics", <metric_name>)``.
        """
        exp_output: List = []
        test_output: List = []

        for exp in self:
            exp_output.append(
                {
                    ("name", ""): exp["name"],
                    ("short_slug", ""): exp["short_slug"],
                    ("slug", ""): exp["slug"],
                    ("author", ""): exp["author"],
                    ("last_updated_by", ""): exp["last_updated_by"],
                    ("created_at", ""): exp["created_at"],
                    ("last_updated", ""): exp["last_updated"],
                    **{
                        ("metrics", key): value for key, value in exp["metrics"].items()
                    },
                    **{
                        ("parameters", key): value
                        for key, value in exp["parameters"].items()
                        if not isinstance(value, (tuple, list, dict))
                    },
                }
            )
            for test in exp["tests"]:
                test_output.append(
                    {
                        ("name", ""): exp["name"],
                        ("short_slug", ""): exp["short_slug"],
                        ("slug", ""): exp["slug"],
                        ("test", ""): test["name"],
                        ("description", ""): test["description"],
                        **{
                            ("metrics", key): value
                            for key, value in test["metrics"].items()
                        },
                    }
                )

        return exp_output, test_output

    def __contains__(self, item: str) -> bool:
        """Check if the project contains an experiment with the given slug or short slug."""
        for exp in self.experiments:
            if exp.slug == item or exp.short_slug == item:
                out = True
                break
        else:
            out = False

        return out

    def __getitem__(self, arg: str) -> Union[Experiment, ReadOnlyExperiment]:
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
        for exp in self.experiments:
            if exp.slug == arg or exp.short_slug == arg:
                out = exp
                break
        else:
            raise KeyError(f"No experiment with slug {arg}")

        return out

    def __iter__(self):
        """Iterate through each experiment and return the dictionary."""
        for exp in self.experiments:
            yield exp.to_dict()
