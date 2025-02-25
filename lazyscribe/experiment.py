"""Experiment dataclass."""

import getpass
import inspect
import json
import logging
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

from attrs import Factory, asdict, define, field, fields, filters, frozen
from fsspec.implementations.local import LocalFileSystem
from fsspec.spec import AbstractFileSystem
from slugify import slugify

from lazyscribe._utils import serializer, utcnow
from lazyscribe.artifacts import Artifact, _get_handler
from lazyscribe.exception import ArtifactLoadError, ArtifactLogError
from lazyscribe.test import ReadOnlyTest, Test

LOG = logging.getLogger(__name__)


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
    created_at : datetime, optional (default ``utcnow()``)
        When the experiment was created.
    last_updated : datetime, optional (default ``utcnow()``)
        When the experiment was last updated.
    dependencies : dict, optional (default None)
        A dictionary of upstream project experiments. The key is the short slug for the upstream
        experiment and the value is an :class:`Experiment` instance.
    """

    name: str
    project: Path = field(eq=False)
    dir: Path = field(eq=False)
    fs: AbstractFileSystem = field(eq=False)
    author: str = Factory(getpass.getuser)
    last_updated_by: str = field()
    metrics: dict = Factory(lambda: {})
    parameters: dict = Factory(lambda: {})
    created_at: datetime = Factory(utcnow)
    last_updated: datetime = Factory(utcnow)
    dependencies: dict = field(eq=False, factory=lambda: {})
    short_slug: str = field()
    slug: str = field()
    tests: list[Union[Test, ReadOnlyTest]] = Factory(lambda: [])
    artifacts: list[Artifact] = Factory(factory=lambda: [])
    tags: list[str] = Factory(factory=lambda: [])
    dirty: bool = field(eq=False, factory=lambda: True)

    @dir.default
    def _dir_factory(self) -> Path:
        """Get the default directory for the project and experiment.

        Returns
        -------
        Path
            Absolute path to the directory.
        """
        return self.project.parent

    @fs.default
    def _fs_default(self) -> AbstractFileSystem:
        """Define a default local filesystem implementation.

        Returns
        -------
        LocalFileSystem
            A standard local filesystem through ``fsspec``.
        """
        return LocalFileSystem()

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

        This method will overwrite existing keys.

        Parameters
        ----------
        name : str
            Name of the metric.
        value : int or float
            Value of the metric.
        """
        self.last_updated = utcnow()
        self.metrics[name] = value

        self.dirty = True

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
        self.last_updated = utcnow()
        self.parameters[name] = value

        self.dirty = True

    def tag(self, *args, overwrite: bool = False):
        """Add one or more tags to the experiment.

        .. important::

            If this function is called with no supplied values for ``*args``
            _and_ ``overwrite=True``, the result will be that the experiment has
            no associated tags.

        Parameters
        ----------
        *args
            The tags.
        overwrite : bool, optional (default False)
            Whether to add or overwrite the new tags.
        """
        self.last_updated = utcnow()
        new_tags_ = list(args)
        if overwrite:
            self.tags = new_tags_
        else:
            self.tags += new_tags_

        self.dirty = True

    def log_artifact(
        self,
        name: str,
        value: Any,
        handler: str,
        fname: Optional[str] = None,
        overwrite: bool = False,
        **kwargs,
    ):
        """Log an artifact to the experiment.

        This method associates an artifact with the experiment, but the artifact will
        not be written until :py:meth:`lazyscribe.Project.save` is called.

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

        Raises
        ------
        ArtifactLogError
            Raised if an artifact is supplied with the same name as an existing artifact and
            ``overwrite`` is set to ``False``.
        """
        # Retrieve and construct the handler
        self.last_updated = utcnow()
        self.dirty = True
        handler_cls = _get_handler(handler)
        artifact_handler = handler_cls.construct(
            name=name,
            value=value,
            fname=fname,
            created_at=self.last_updated,
            writer_kwargs=kwargs,
        )
        for index, artifact in enumerate(self.artifacts):
            if artifact.name == name:
                if overwrite:
                    self.artifacts[index] = artifact_handler
                    if handler_cls.output_only:
                        warnings.warn(
                            f"Artifact '{name}' is added. It is not meant to be read back as Python Object",
                            UserWarning,
                            stacklevel=2,
                        )
                    break
                else:
                    raise ArtifactLogError(
                        f"An artifact with name {name} already exists in the experiment. Please "
                        "use another name or set ``overwrite=True`` to replace the artifact."
                    )
        else:
            self.artifacts.append(artifact_handler)
            if handler_cls.output_only:
                warnings.warn(
                    f"Artifact '{name}' is added. It is not meant to be read back as Python Object",
                    UserWarning,
                    stacklevel=2,
                )

    def load_artifact(self, name: str, validate: bool = True, **kwargs) -> Any:
        """Load a single artifact.

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

        Raises
        ------
        ArtifactLoadError
            If ``validate`` and runtime environment does not match artifact metadata.
            Or if there is no artifact found with the name provided.
        """
        for artifact in self.artifacts:
            if artifact.name == name:
                # Construct the handler with relevant parameters.
                artifact_attrs = {
                    x: y
                    for x, y in inspect.getmembers(artifact)
                    if not x.startswith("_") and not inspect.ismethod(y)
                }
                exclude_params = ["value", "fname", "created_at", "dirty"]
                construct_params = [
                    param
                    for param in inspect.signature(artifact.construct).parameters
                    if param not in exclude_params
                ]
                artifact_attrs = {
                    key: value
                    for key, value in artifact_attrs.items()
                    if key in construct_params
                }

                curr_handler = type(artifact).construct(**artifact_attrs, dirty=False)

                # Validate the handler
                if validate and curr_handler != artifact:
                    field_filters = filters.exclude(
                        fields(type(artifact)).name,
                        fields(type(artifact)).fname,
                        fields(type(artifact)).value,
                        fields(type(artifact)).created_at,
                        fields(type(artifact)).dirty,
                    )
                    raise ArtifactLoadError(
                        "Runtime environments do not match. Artifact parameters:\n\n"
                        f"{json.dumps(asdict(artifact, filter=field_filters))}"
                        "\n\nCurrent parameters:\n\n"
                        f"{json.dumps(asdict(curr_handler, filter=field_filters))}"
                    )
                # Read in the artifact
                mode = "rb" if curr_handler.binary else "r"
                with self.fs.open(str(self.path / artifact.fname), mode) as buf:
                    out = curr_handler.read(buf, **kwargs)
                if artifact.output_only:
                    warnings.warn(
                        f"Artifact '{name}' is not the original Python Object",
                        UserWarning,
                        stacklevel=2,
                    )
                break
        else:
            raise ArtifactLoadError(f"No artifact with name {name}")

        return out

    @contextmanager
    def log_test(self, name: str, description: Optional[str] = None) -> Iterator[Test]:
        """Add a test to the experiment using a context handler.

        A test is a specific location for non-global metrics.

        Parameters
        ----------
        name : str
            Name of the test.
        description : str, optional (default None)
            An optional description for the test.

        Yields
        ------
        Test
            The :py:class:`lazyscribe.test.Test` dataclass.
        """
        test = Test(name=name, description=description)

        yield test

        self.last_updated = utcnow()
        self.tests.append(test)

        self.dirty = True

    def to_dict(self) -> dict:
        """Serialize the experiment to a dictionary.

        Returns
        -------
        dict
            The experiment dictionary.
        """
        return asdict(
            self,
            value_serializer=serializer,
            filter=filters.exclude(
                fields(Experiment).dir,
                fields(Experiment).project,
                fields(Experiment).fs,
                fields(Experiment).dirty,
            ),
        )

    def to_tabular(self) -> dict:
        """Create a dictionary that can be fed into ``pandas``.

        Returns
        -------
        dict
            Represent the experiment, with the following keys:

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

            as well as one key per parameter in the ``parameters`` dictionary
            (with the format ``("parameters", <parameter_name>)``) and one key
            per metric in the ``metrics`` dictionary (with the format
            ``("metrics", <metric_name>)``) for each experiment.
        """
        d = self.to_dict()
        return {
            ("name", ""): d["name"],
            ("slug", ""): d["slug"],
            ("short_slug", ""): d["short_slug"],
            ("author", ""): d["author"],
            ("created_at", ""): d["created_at"],
            ("last_updated", ""): d["last_updated"],
            ("last_updated_by", ""): d["last_updated_by"],
            **{
                ("parameters", key): value
                for key, value in d["parameters"].items()
                if not isinstance(value, (tuple, list, dict))
            },
            **{("metrics", key): value for key, value in d["metrics"].items()},
        }

    def __str__(self):
        """Shortened string representation."""
        return f"<lazyscribe.experiment.Experiment at {hex(id(self))}>"

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

    def __str__(self):
        """Shortened string representation."""
        return f"<lazyscribe.experiment.ReadOnlyExperiment at {hex(id(self))}>"
