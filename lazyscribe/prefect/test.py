"""Prefect test tasks."""

from typing import Optional, Union

from prefect import Task, task
from prefect.utilities.tasks import defaults_from_attrs

from ..test import Test


@task(name="Log test metric")
def log_test_metric(test: Test, name: str, value: Union[float, int]):
    """Log a non-global metric to a test.

    Parameters
    ----------
    test : Test
        The instantiated :py:class:`lazyscribe.test.Test` object.
    name : str
        Name of the metric.
    value : float or int
        Metric value.
    """
    test.log_metric(name, value)


class LazyTest(Task):
    """Prefect integration for logging ``lazyscribe`` tests.

    This task should only be used to instantiate new tests.

    Parameters
    ----------
    description : str, optional (default None)
        Description of the test.
    **kwargs
        Keyword arguments for :py:class:`prefect.Task`.
    """

    def __init__(self, description: Optional[str] = None, **kwargs):
        """Init method."""
        self.description = description

        super().__init__(**kwargs)

    @defaults_from_attrs("name", "description")
    def run(
        self, name: Optional[str] = None, description: Optional[str] = None
    ) -> Test:
        """Instantiate a new :py:class:`lazyscribe.test.Test` object.

        Parameters
        ----------
        name : str, optional (default None)
            The name of the test. Defaults to the task name.
        description : str, optional (default None)
            Description of the test.

        Returns
        -------
        Test
            Instantiated :py:class:`lazyscribe.test.Test` object.
        """
        if name is None:
            raise ValueError("Please supply a valid name.")

        return Test(name=name, description=description)

    def log_metric(self, name: str, value: Union[float, int]):
        """Add a ``log_metric`` task.

        Parameters
        ----------
        name : str
            The name of the metric.
        value : float or int
            The metric value.
        """
        log_test_metric(self, name, value)
