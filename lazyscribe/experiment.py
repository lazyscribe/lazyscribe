"""Experiment dataclass."""

from datetime import datetime
import getpass
import logging
from pathlib import Path
from typing import Any, Dict, Union

from attrs import define, field, frozen, Factory
from slugify import slugify

LOG = logging.getLogger(__name__)

# TODO: Add dependencies

@define(order=True)
class Experiment:
    """Experiment data class.

    This class is not meant to be initialized directly. It is meant to be used through the
    :py:class:`lazyscribe.project.Project` class.

    Parameters
    ----------
    name : str
        The name of the experiment.
    dir : Path
        The directory in which the project resides. Used to provide the ``path`` attribute.
    author : str, optional (default ``getpass.getuser()``)
        The author of the experiment.
    metrics : dict, optional (default {})
        A dictionary of metric values. Each metric value can be an individual value or a list.
    parameters : dict, optional (default {})
        A dictionary of experiment parameters. The key must be a string but the value can be
        anything.
    created_at : datetime, optional (default ``datetime.now()``)
        When the experiment was created.
    last_updated : datetime, optional (default ``datetime.now()``)
        When the experiment was last updated.
    dependencies : dict, optional (default None)
        A dictionary of upstream project experiments. The key is the short slug for the upstream
        experiment and the value is an :class:`Experiment` instance.
    """

    name: str
    dir: Path = field(eq=False, factory=Path().resolve)
    author: str = Factory(getpass.getuser)
    metrics: Dict = Factory(lambda: {})
    parameters: Dict = Factory(lambda: {})
    created_at: datetime = Factory(datetime.now)
    last_updated: datetime = field(order=True, factory=datetime.now)
    dependencies: Dict = Factory(lambda: {})
    short_slug: str = field()
    slug: str = field()

    @short_slug.default
    def _short_slug_factory(self) -> str:
        """Get the short slug.

        Returns
        -------
        str
            The slugified experiment name.
        """
        return slugify(self.name)

    @slug.default
    def _slug_factory(self) -> str:
        """Get the full experiment slug.

        Returns
        -------
        str
            Experiment slug, in the format `{name}-{created_at}-{author}`.
        """
        return slugify(
            f"{self.name}-{self.created_at.strftime('%Y%m%d%H%M%S')}-{self.author}"
        )

    @property
    def path(self) -> Path:
        """The path to an experiment folder.

        On retrieval, this property function will create the
        experiment folder if necessary.

        Returns
        -------
        Path
            The path for the experiment.
        """
        out = self.dir / self.name  # TODO: Change to slug
        out.mkdir(exist_ok=True)

        return out

    def log_metric(self, name: str, value: Union[float, int]):
        """Log a metric to the experiment.

        If the ``name`` exists in the ``metrics`` dictionary, the value will be
        appended to a list.

        Parameters
        ----------
        name : str
            Name of the metric.
        value : int or float
            Value of the metric.
        """
        self.last_updated = datetime.now()
        if name in self.metrics:
            if not isinstance(self.metrics[name], list):
                self.metrics[name] = [self.metrics[name]]
            self.metrics[name].append(value)
        else:
            self.metrics[name] = value


    def log_parameter(self, name: str, value: Any):
        """Log a parameter to the experiment.
        
        This method will overwrite existing keys.

        Parameters
        ----------
        name : str
            The name of the parameter.
        value : Any
            The parameter itself.
        """
        self.last_updated = datetime.now()
        if name in self.parameters:
            LOG.warning(f"Overwriting existing value for {name}")
        self.parameters[name] = value


@frozen
class ReadOnlyExperiment(Experiment):
    """Immutable version of an experiment."""
