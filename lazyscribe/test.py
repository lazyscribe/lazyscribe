"""Sub-population tests."""

from __future__ import annotations

from typing import Any

from attrs import Factory, asdict, define, field, frozen

from lazyscribe._utils import serializer


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
    metrics : dict[str, float | int], optional (default {})
        A dictionary of metric values. Each metric value can be an individual value or a list.
    parameters : dict[str, Any], optional (default {})
        A dictionary of test parameters. The key must be a string but the value can be anything.
    """

    # Tell pytest it's not a Python test class
    __test__ = False

    name: str = field()
    description: str | None = Factory(lambda: None)
    metrics: dict[str, float | int] = Factory(lambda: {})
    parameters: dict[str, Any] = Factory(lambda: {})

    def log_metric(self, name: str, value: float | int) -> None:
        """Log a metric to the test.

        This method will overwrite existing keys.

        Parameters
        ----------
        name : str
            Name of the metric.
        value : int | float
            Value of the metric.
        """
        self.metrics[name] = value

    def __str__(self) -> str:
        """Shortened string representation."""
        return f"<lazyscribe.test.Test at {hex(id(self))}>"

    def log_parameter(self, name: str, value: Any) -> None:
        """Log a parameter to the test.

        This method will overwrite existing keys.

        Parameters
        ----------
        name : str
            The name of the parameter.
        value : Any
            The parameter itself.
        """
        self.parameters[name] = value

    def to_dict(self) -> dict[str, Any]:
        """Serialize the test to a dictionary.

        Returns
        -------
        dict[str, Any]
            The test dictionary.
        """
        return asdict(
            self,
            value_serializer=serializer,
        )


@frozen
class ReadOnlyTest(Test):
    """Immutable version of the test."""

    def __str__(self) -> str:
        """Shortened string representation."""
        return f"<lazyscribe.test.ReadOnlyTest at {hex(id(self))}>"
