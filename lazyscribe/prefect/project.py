"""Prefect project tasks."""

from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlparse

import prefect
from prefect import Flow, Task, task
from prefect.utilities.tasks import defaults_from_attrs

from ..experiment import Experiment
from ..project import Project
from .experiment import LazyExperiment


@task(name="Append experiment")
def append_experiment(project: Project, experiment: Experiment):
    """Append an experiment to an existing project.

    Parameters
    ----------
    project : Project
        An existing project in write or append-only mode.
    experiment : Experiment
        An experiment.
    """
    project.append(experiment)


@task(name="Save project")
def save_project(project: Project):
    """Save the project.

    Parameters
    ----------
    project : Project
        The project to save.
    """
    project.save()


@task(name="Merge projects")
def merge_projects(base: Project, other: Project) -> Project:
    """Merge two projects.

    Parameters
    ----------
    base : Project
        The base project for the merge.
    other : Project
        The second project for the merge.

    Returns
    -------
    Project
        The merged project.
    """
    return base.merge(other)


@task(name="Create tabular data", nout=2)
def project_to_tabular(project: Project) -> Tuple[List, List]:
    """Create tabular representations of the project.

    Parameters
    ----------
    project : Project
        The project to convert.

    Returns
    -------
    List
        A global project list, with one entry per experiment.
    List
        A tests level list.
    """
    return project.to_tabular()


class LazyProject(Task):
    """Prefect integration for logging ``lazyscribe`` projects.

    Parameters
    ----------
    fpath : str, optional (default "project.json")
        The location of the project file. If not file exists, this will be the location
        of the output JSON file.
    mode : {"r", "a", "w", "w+"}, optional (default "w")
        The mode for opening the project. See :py:class:`lazyscribe.Project` for reference.
    author : str, optional (default None)
        The project author.
    storage_options : Dict, optional (default None)
        Storage options to pass to the filesystem initialization.
    **kwargs
        Keyword arguments for :py:class:`prefect.Task`.
    """

    def __init__(
        self,
        fpath: str = "project.json",
        mode: str = "w",
        author: Optional[str] = None,
        storage_options: Optional[Dict] = None,
        **kwargs
    ):
        """Init method."""
        self.fpath = fpath
        self.mode = mode
        self.author = author
        self.storage_options = storage_options

        super().__init__(**kwargs)

    @defaults_from_attrs("fpath", "mode", "author", "storage_options")
    def run(
        self,
        fpath: Optional[str] = None,
        mode: Optional[str] = None,
        author: Optional[str] = None,
        storage_options: Optional[Dict] = None,
    ) -> Project:
        """Instantiate a :py:class:`lazyscribe.Project`.

        Parameters
        ----------
        fpath : str, optional (default None)
            The location of the project JSON file.
        mode : str, optional (default None)
            The mode for opening the project.
        author : str, optional (default None)
            The author for the project.
        storage_options : Dict, optional (default None)
            Storage options to pass to the filesystem initialization.

        Returns
        -------
        Project
            The instantiated project.
        """
        # Keep fpath in passed form so Project can parse the fs scheme
        if fpath is None:
            raise ValueError("Please supply a valid fpath value.")
        if mode is None:
            raise ValueError("Please supply a valid mode value.")

        return Project(fpath=fpath, mode=mode, author=author, **storage_options or {})

    def save(self, flow: Optional[Flow] = None):
        """Add a ``save_project`` task to the flow.

        Parameters
        ----------
        flow : Flow, optional (default None)
            A :py:class:`prefect.Flow` object. If not supplied, this function will
            retrieve a flow from ``prefect.context``.
        """
        # Find all instances of ``append_experiment`` and bind as upstream tasks
        flow = flow or prefect.context.get("flow")
        if not flow:
            raise ValueError("Could not infer an active flow context.")

        save_project(self, upstream_tasks=flow.get_tasks(name="Append experiment"))

    def merge(self, other: Project, flow: Optional[Flow] = None):
        """Add a ``merge_projects`` task to the flow.

        Parameters
        ----------
        other : Project
            The other project.
        flow : Flow, optional (default None)
            A :py:class:`prefect.Flow` object. If not supplied, this function will
            retrieve a flow from ``prefect.context``.

        Returns
        -------
        Task
            The bound :py:meth:`lazyscribe.prefect.merge_projects` task.
        """
        # Find all instances of ``append_experiment`` and bind as upstream tasks
        flow = flow or prefect.context.get("flow")
        if not flow:
            raise ValueError("Could not infer an active flow context.")

        return merge_projects(
            self, other, upstream_tasks=flow.get_tasks(name="Append experiment")
        )

    def append(self, other: Task, **kwargs):
        """Add an ``append_experiment`` task to the flow.

        Parameters
        ----------
        other : Task
            The new experiment to add.
        **kwargs
            Keyword arguments for :py:meth:`prefect.task`.
        """
        append_experiment(self, other, **kwargs)

    def to_tabular(self, flow: Optional[Flow] = None) -> Task:
        """Add a ``project_to_tabular`` task to the flow.

        Parameters
        ----------
        flow : Flow, optional (default None)
            A :py:class:`prefect.Flow` object. If not supplied, this function will
            retrieve a flow from ``prefect.context``.

        Returns
        -------
        Task
            The project-level list.
        Task
            The test-level list.
        """
        # Find all instances of ``append_experiment`` and bind as upstream tasks
        flow = flow or prefect.context.get("flow")
        if not flow:
            raise ValueError("Could not infer an active flow context.")

        return project_to_tabular(
            self, upstream_tasks=flow.get_tasks(name="Append experiment")
        )

    @contextmanager
    def log(
        self,
        name: str,
        project: Optional[str] = None,
        author: Optional[str] = None,
        flow: Optional[Flow] = None,
    ) -> Iterator[Task]:
        """Add a :py:class:`lazyscribe.prefect.LazyExperiment` to the flow.

        On exit from the context handler, an additional task will be added to
        append the experiment to the project itself.

        Parameters
        ----------
        name : str
            The name of the experiment.
        project : str, optional (default None)
            The location of the project JSON. If you have parameterized the project
            location, re-supply it here.
        author : str, optional (default None)
            The author of the project. If you have parameterized the author, please
            re-supply it here.
        flow : Flow, optional (default None)
            A :py:class:`prefect.Flow` object. If not supplied, this function will
            retrieve a flow from ``prefect.context``.

        Returns
        -------
        LazyExperiment
            An instantiated :py:class:`lazyscribe.prefect.LazyExperiment` object.
            This task has already been added to the flow.
        """
        # Convert string to Path, if necessary
        if project is None:
            if isinstance(self.fpath, str):
                parsed = urlparse(self.fpath)
                fpath = Path(parsed.netloc + parsed.path)
            else:
                fpath = self.fpath
        elif isinstance(project, str):
            parsed = urlparse(project)
            fpath = Path(parsed.netloc + parsed.path)
        elif isinstance(project, Path):
            fpath = project
        else:
            raise ValueError("Please supply a valid project value.")

        experiment = LazyExperiment(name=name)(
            project=fpath, author=author or self.author, upstream_tasks=[self]
        )

        try:
            yield experiment
        finally:
            flow = flow or prefect.context.get("flow")
            if not flow:
                raise ValueError("Could not infer an active flow context.")

            self.append(experiment, upstream_tasks=flow.downstream_tasks(experiment))
