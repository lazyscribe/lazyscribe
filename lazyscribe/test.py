"""Sub-population tests."""

from typing import Any, Optional, Union

from attrs import Factory, asdict, define, frozen

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
    metrics : dict, optional (default {})
        A dictionary of metric values. Each metric value can be an individual value or a list.
    parameters : dict, optional (default {})
        A dictionary of test parameters. The key must be a string but the value can be anything.
    """

    # Tell pytest it's not a Python test class
    __test__ = False

    name: str
    description: Optional[str] = Factory(lambda: None)
    metrics: dict = Factory(lambda: {})
    parameters: dict = Factory(lambda: {})

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

    def __str__(self):
        """Shortened string representation."""
        return f"<lazyscribe.test.Test at {hex(id(self))}>"

    def log_parameter(self, name: str, value: Any):
        """Log a parameter to the test.

        This method will overwrite existing keys.

        Parameters
        ----------
        name : str
            The name of the parameter.
        value : any
            The parameter itself.
        """
        self.parameters[name] = value

    def to_dict(self) -> dict:
        """Serialize the test to a dictionary.

        Returns
        -------
        dict
            The test dictionary.
        """
        return asdict(
            self,
            value_serializer=serializer,
        )

    def to_tabular(self) -> dict:
        """Create a dictionary that can be fed into ``pandas``.

        Returns
        -------
        dict
            Represent the test, with the following keys:

            +-------------------------------------+-------------------------------+
            | Field                               | Description                   |
            |                                     |                               |
            +=====================================+===============================+
            | ``("test",)``                       | Test name                     |
            +-------------------------------------+-------------------------------+
            | ``("description",)``                | Test description              |
            +-------------------------------------+-------------------------------+

            as well as one key per parameter in the ``parameters`` dictionary
            (with the format ``("parameters", <parameter_name>)``) and one key
            per metric in the ``metrics`` dictionary (with the format
            ``("metrics", <metric_name>)``) for each test.
        """
        d = self.to_dict()
        return {
            ("test", ""): d["name"],
            ("description", ""): d["description"],
            **{
                ("parameters", key): value
                for key, value in d["parameters"].items()
                if not isinstance(value, (tuple, list, dict))
            },
            **{("metrics", key): value for key, value in d["metrics"].items()},
        }


@frozen
class ReadOnlyTest(Test):
    """Immutable version of the test."""

    def __str__(self):
        """Shortened string representation."""
        return f"<lazyscribe.test.ReadOnlyTest at {hex(id(self))}>"
