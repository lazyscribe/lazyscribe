"""Prefect experiment tasks."""

import getpass
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional, Union

import prefect
from prefect import Flow, Task, task
from prefect.utilities.tasks import defaults_from_attrs

from ..experiment import Experiment
from ..test import Test
from .test import LazyTest


@task(name="Log experiment metric")
def log_experiment_metric(experiment: Experiment, name: str, value: Union[float, int]):
    """Log a metric.

    Parameters
    ----------
    experiment : Experiment
        The experiment.
    name : str
        Name of the metric.
    value : float or int
        The metric value.
    """
    experiment.log_metric(name, value)


@task(name="Log parameter")
def log_parameter(experiment: Experiment, name: str, value: Any):
    """Log a parameter.

    Parameters
    ----------
    experiment : Experiment
        The experiment.
    name : str
        The name of the parameter.
    value : Any
        The parameter value.
    """
    experiment.log_parameter(name, value)


@task(name="Log artifact")
def log_artifact(
    experiment: Experiment,
    name: str,
    value: Any,
    handler: str,
    fname: Optional[str] = None,
    overwrite: bool = False,
    **kwargs
):
    """Log an artifact.

    Parameters
    ----------
    experiment : Experiment
        The experiment.
    name : str
        The name of the artifact.
    value : Any
        The object to persist.
    handler : str
        The name of the handler to use for the object.
    fname: str, optional (default None)
        The filename for the artifact. If not provided, it will be derived from the
        name of the artifact and the builtin suffix for each handler.
    overwrite : bool, optional (default False)
        Whether or not to overwrite an existing artifact with the same name. If set to ``True``,
        the previous artifact will be removed and overwritten with the current artifact.
    **kwargs : dict
        Keyword arguments to use for the write function.
    """
    experiment.log_artifact(name, value, handler, fname, overwrite, **kwargs)


@task(name="Load artifact")
def load_artifact(experiment: Experiment, name: str, validate: bool = True, **kwargs):
    """Load an artifact.

    Parameters
    ----------
    experiment : Experiment
        The experiment.
    name : str
        The name of the artifact to load.
    validate : bool, optional (default True)
        Whether or not to validate the runtime environment against the artifact metadata.
    **kwargs : dict
        Keyword arguments for the handler read function.

    Returns
    -------
    object
        The artifact.
    """
    return experiment.load_artifact(name, validate, **kwargs)


@task(name="Append test")
def append_test(experiment: Experiment, test: Test):
    """Append a test to the experiment.

    Parameters
    ----------
    experiment : Experiment
        The experiment.
    test : Test
        The test object.
    """
    experiment.tests.append(test)


class LazyExperiment(Task):
    """Prefect integration for logging ``lazyscribe`` experiments.

    This task is only meant for creating new experiments.

    Parameters
    ----------
    project : Path
        The path to the project JSON associated with the project.
    author : str, optional (default ``getpass.getuser()``)
        The author of the experiment.
    **kwargs
        Keyword arguments for :py:class:`prefect.Task`.
    """

    def __init__(
        self,
        project: Optional[Path] = None,
        author: Optional[str] = getpass.getuser(),
        **kwargs
    ):
        """Init method."""
        self.project = project
        self.author = author

        super().__init__(**kwargs)

    @defaults_from_attrs("name", "project", "author")
    def run(
        self,
        name: Optional[str] = None,
        project: Optional[Path] = None,
        author: Optional[str] = None,
    ) -> Experiment:
        """Instantiate a new experiment.

        Parameters
        ----------
        name : str, optional (default None)
            The name of the experiment. Defaults to the task name.
        project : Path, optional (default None)
            The project JSON path. Defaults to the class attribute.
        author : str, optional (default None)
            The author. Defaults to the class attribute.

        Returns
        -------
        Experiment
            The :py:class:`lazyscribe.Experiment` class.
        """
        if name is None:
            raise ValueError("Please supply a valid name value.")
        if not isinstance(project, Path):
            raise ValueError("Please supply a valid project path.")
        if author is None:
            raise ValueError("Please supply a valid author.")

        return Experiment(name=name, project=project, author=author)

    def log_metric(self, name: str, value: Union[float, int]):
        """Add a ``log_metric`` task.

        Parameters
        ----------
        name : str
            Name of the metric.
        value : int or float
            Value of the metric.
        """
        log_experiment_metric(self, name, value)

    def log_parameter(self, name: str, value: Any):
        """Add a ``log_parameter`` task.

        Parameters
        ----------
        name : str
            Name of the parameter.
        value : Any
            The parameter itself.
        """
        log_parameter(self, name, value)

    def log_artifact(
        self,
        name: str,
        value: Any,
        handler: str,
        fname: Optional[str] = None,
        overwrite: bool = False,
        **kwargs
    ):
        """Add a ``log_artifact`` task.

        Parameters
        ----------
        name : str
            The name of the artifact.
        value : Any
            The object to persist to the filesystem.
        handler : str
            The name of the handler to use for the object.
        fname : str, optional (default None)
            The filename for the artifact. If not provided, it will be derived from the
            name of the artifact and the builtin suffix for each handler.
        overwrite : bool, optional (default False)
            Whether or not to overwrite an existing artifact with the same name. If set to ``True``,
            the previous artifact will be removed and overwritten with the current artifact.
        **kwargs : dict
            Keyword arguments for the write function of the handler.
        """
        log_artifact(self, name, value, handler, fname, overwrite, **kwargs)

    def load_artifact(self, name: str, validate: bool = True, **kwargs):
        """Add a ``load_artifact`` task.

        Parameters
        ----------
        name : str
            The name of the artifact to load.
        validate : bool, optional (default True)
            Whether or not to validate the runtime environment against the artifact
            metadata.
        **kwargs : dict
            Keyword arguments for the handler read function.

        Returns
        -------
        object
            The artifact.
        """
        return load_artifact(self, name, validate, **kwargs)

    @contextmanager
    def log_test(
        self, name: str, description: Optional[str] = None, flow: Optional[Flow] = None
    ) -> Iterator[Task]:
        """Add a :py:class:`lazyscribe.prefect.LazyTest` task to the flow.

        On exit from the context handler, an additional task will be added to append
        the test to the experiment itself.

        Parameters
        ----------
        name : str
            Name of the test.
        description : str, optional (default None)
            A description of the test.
        flow : Flow, optional (default None)
            A :py:class:`prefect.Flow` object. If not supplied, this function will retrieve
            a flow from ``prefect.context``.

        Returns
        -------
        LazyTest
            An instantiated :py:class:`lazyscribe.prefect.LazyTest` object. This task
            has already been added to the flow.
        """
        test = LazyTest(name=name, description=description)()

        try:
            yield test
        finally:
            flow = flow or prefect.context.get("flow")
            if not flow:
                raise ValueError("Could not infer an active flow context.")

            append_test(self, test, upstream_tasks=flow.downstream_tasks(test))
