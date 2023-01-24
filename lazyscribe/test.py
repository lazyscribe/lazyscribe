"""Sub-population tests."""

from typing import Dict, Optional, Union

from attrs import Factory, define, frozen


@define
class Test:
    """Sub-population tests.

    These objects should only be instantiated within an experiment. A test is associated with
    some subset of the entire experiment. For example, a test could be used to evaluate the
    performance of a model against a specific subpopulation.

    Parameters
    ----------
    name : str
        The name of the test.
    description : str, optional (default None)
        A description of the test.
    metrics : dict, optional (default {})
        A dictionary of metric values. Each metric value can be an individual value or a list.
    """

    name: str
    description: Optional[str] = Factory(lambda: None)
    metrics: Dict = Factory(lambda: {})

    def log_metric(self, name: str, value: Union[float, int]):
        """Log a metric to the test.

        This method will overwrite existing keys.

        Parameters
        ----------
        name : str
            Name of the metric.
        value : int or float
            Value of the metric.
        """
        self.metrics[name] = value


@frozen
class ReadOnlyTest(Test):
    """Immutable version of the test."""
