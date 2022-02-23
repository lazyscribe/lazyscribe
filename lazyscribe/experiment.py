"""Experiment dataclass."""

from datetime import datetime
import getpass
import logging
from pathlib import Path
from typing import Any, Dict, Union

from attrs import asdict, define, field, frozen, Factory
from slugify import slugify

LOG = logging.getLogger(__name__)


def serializer(inst, field, value):
    """Datetime and dependencies converter for :meth:`attrs.asdict`.

    Parameters
    ----------
    inst
        Included for compatibility.
    field
        The field name.
    value
        The field value.

    Returns
    -------
    Any
        Converted value for easy serialization.
    """
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if field is not None and field.name == "dependencies":
        new = [f"{exp.project}|{exp.slug}" for exp in value.values()]
        return new

    return value


@define
class Experiment:
    """Experiment data class.

    This class is not meant to be initialized directly. It is meant to be used through the
    :py:class:`lazyscribe.project.Project` class.

    Parameters
    ----------
    name : str
        The name of the experiment.
    project : Path
        The path to the project JSON associated with the project.
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
    project: Path = field(eq=False)
    dir: Path = field(eq=False)
    author: str = Factory(getpass.getuser)
    last_updated_by: str = field()
    metrics: Dict = Factory(lambda: {})
    parameters: Dict = Factory(lambda: {})
    created_at: datetime = Factory(datetime.now)
    last_updated: datetime = Factory(datetime.now)
    dependencies: Dict = field(eq=False, factory=lambda: {})
    short_slug: str = field()
    slug: str = field()

    @dir.default
    def _dir_factory(self) -> Path:
        """Get the default directory for the project and experiment.

        Returns
        -------
        Path
            Absolute path to the directory.
        """
        return self.project.parent

    @last_updated_by.default
    def _last_updated_by_factory(self) -> str:
        """Last editor."""
        return self.author

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
        return slugify(f"{self.name}-{self.created_at.strftime('%Y%m%d%H%M%S')}")

    @property
    def path(self) -> Path:
        """Path to an experiment folder.

        This folder can be used to store any plots or artifacts that you want to associate
        with the experiment.

        Returns
        -------
        Path
            The path for the experiment.
        """
        return self.dir / self.slug

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
        self.parameters[name] = value

    def to_dict(self) -> Dict:
        """Serialize the experiment to a dictionary.

        Returns
        -------
        Dict
            The experiment dictionary.
        """
        return asdict(
            self,
            value_serializer=serializer,
            filter=lambda attr, _: attr.name not in ["dir", "project"],
        )

    def __gt__(self, other):
        """Determine whether this experiment is newer than another experiment.

        If the experiments have the same ``slug``, this function will compare using the
        ``last_updated`` attribute. If the ``slug`` is different, this function will use
        the ``created_at`` value.
        """
        if self.slug == other.slug:
            return self.last_updated > other.last_updated
        else:
            return self.created_at > other.created_at

    def __lt__(self, other):
        """Determine whether this experiment is older than another experiment.

        If the experiments have the same ``slug``, this function will compare using the
        ``last_updated`` attribute. If the ``slug`` is different, this function will use
        the ``created_at`` value.
        """
        if self.slug == other.slug:
            return self.last_updated < other.last_updated
        else:
            return self.created_at < other.created_at

    def __ge__(self, other):
        """Determine whether this experiment is newer than another experiment.

        If the experiments have the same ``slug``, this function will compare using the
        ``last_updated`` attribute. If the ``slug`` is different, this function will use
        the ``created_at`` value.
        """
        return bool(self == other or self > other)

    def __le__(self, other):
        """Determine whether this experiment is older than another experiment.

        If the experiments have the same ``slug``, this function will compare using the
        ``last_updated`` attribute. If the ``slug`` is different, this function will use
        the ``created_at`` value.
        """
        return bool(self == other or self < other)


@frozen
class ReadOnlyExperiment(Experiment):
    """Immutable version of an experiment."""
