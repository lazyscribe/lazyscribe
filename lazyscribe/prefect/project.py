"""Prefect project tasks."""

from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Tuple

import prefect
from prefect import task, Flow, Task
from prefect.utilities.tasks import defaults_from_attrs

from .experiment import LazyExperiment
from ..experiment import Experiment
from ..project import Project


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
    **kwargs
        Keyword arguments for :py:class:`prefect.Task`.
    """

    def __init__(
        self,
        fpath: str = "project.json",
        mode: str = "w",
        author: Optional[str] = None,
        **kwargs
    ):
        """Init method."""
        self.fpath = fpath
        self.mode = mode
        self.author = author

        super().__init__(**kwargs)

    @defaults_from_attrs("fpath", "mode", "author")
    def run(
        self,
        fpath: Optional[str] = None,
        mode: Optional[str] = None,
        author: Optional[str] = None,
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

        Returns
        -------
        Project
            The instantiated project.
        """
        # Convert string to Path, if necessary
        if not isinstance(fpath, Path):
            fpath = Path(fpath)

        return Project(fpath=fpath, mode=mode, author=author)

    def save(self):
        """Add a ``save_project`` task to the flow."""
        save_project(self)

    def merge(self, other: Project):
        """Add a ``merge_projects`` task to the flow.

        Parameters
        ----------
        other : Project
            The other project.
        """
        merge_projects(self, other)

    def append(self, other: Experiment):
        """Add an ``append_experiment`` task to the flow.

        Parameters
        ----------
        other : Experiment
            The new experiment to add.
        """
        append_experiment(self, other)

    def to_tabular(self) -> Tuple[Task, Task]:
        """Add a ``project_to_tabular`` task to the flow.

        Returns
        -------
        Task
            The project-level list.
        Task
            The test-level list.
        """
        return project_to_tabular(self)

    @contextmanager
    def log(
        self,
        name: str,
        project: Optional[str] = None,
        author: Optional[str] = None,
        flow: Optional[Flow] = None,
    ) -> LazyExperiment:
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
        project = project or self.fpath
        if not isinstance(project, Path):
            project = Path(project)
        experiment = LazyExperiment(name=name)(
            project=project, author=author or self.author
        )

        try:
            yield experiment
        finally:
            flow = flow or prefect.context.get("flow")
            if not flow:
                raise ValueError("Could not infer an active flow context.")

            append_experiment(self, experiment, upstream_tasks=flow.downstream_tasks(experiment))
