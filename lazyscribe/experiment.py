"""Experiment dataclass."""

from __future__ import annotations

import getpass
import logging
import os
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from copy import copy
from datetime import datetime
from pathlib import Path
from typing import Any

from attrs import (
    Factory,
    asdict,
    define,
    evolve,
    field,
    fields,
    filters,
    frozen,
)
from fsspec.implementations.local import LocalFileSystem
from fsspec.spec import AbstractFileSystem
from slugify import slugify

from lazyscribe._utils import serializer, utcnow, validate_artifact_environment
from lazyscribe.artifacts import _get_handler
from lazyscribe.artifacts.base import Artifact
from lazyscribe.exception import ArtifactLoadError, ArtifactLogError, SaveError
from lazyscribe.repository import Repository
from lazyscribe.test import Test

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
    project : pathlib.Path
        The path to the project JSON associated with the project.
    dir : pathlib.Path, optional (default None)
        Directory for the project and the experiment. If not supplied, the parent directory for the ``project`` file
        will be used.
    author : str, optional (default ``getpass.getuser()``)
        The author of the experiment.
    last_updated_by : str, optional (default None)
        Last editor of the experiment. If not supplied, the ``author`` will be used.
    metrics : dict[str, float | int], optional (default {})
        A dictionary of metric values. Each metric value can be an individual value or a list.
    parameters : dict[str, Any], optional (default {})
        A dictionary of experiment parameters. The key must be a string but the value can be
        anything.
    created_at : datetime.datetime, optional (default ``lazyscribe._utils.utcnow()``)
        When the experiment was created (in UTC).
    last_updated : datetime.datetime, optional (default ``lazyscribe._utils.utcnow()``)
        When the experiment was last updated (in UTC).
    short_slug : str, optional (default None)
        Slugified ``name``. Defaults to calling :py:meth:`slugify.slugify` on the ``name`` attribute.
    slug : str, optional (default None)
        Unique identifier for the experiment. Defaults to the slugified ``name`` with the creation date
        appended in the format ``YYYYMMDDHHMMSS``.
    tags : list[str], optional (default [])
        Tags for filtering and identifying experiments across a project.
    dependencies : dict[str, lazyscribe.experiment.Experiment], optional (default {})
        A dictionary of upstream project experiments. The key is the short slug for the upstream
        experiment and the value is an :py:class:`Experiment` instance.
    tests : list[lazyscribe.test.Test], optional (default [])
        List of :py:class:`lazyscribe.test.Test` objects corresponding to sub-population/non-global metrics.
    artifacts : list[lazyscribe.artifacts.base.Artifact], optional (default [])
        List of :py:class:`lazyscribe.artifact.base.Artifact` objects corresponding to experimental artifacts.
    dirty : bool, optional (default True)
        Whether or not this experiment should be saved when :py:meth:`lazyscribe.project.Project.save`
        is called. This decision is based on whether the experiment is new or has been updated.
    """

    name: str = field()
    project: Path = field(eq=False)
    dir: Path = field(eq=False)
    fs: AbstractFileSystem = field(eq=False)
    author: str = Factory(getpass.getuser)
    last_updated_by: str = field()
    metrics: dict[str, float | int] = Factory(lambda: {})
    parameters: dict[str, Any] = Factory(lambda: {})
    created_at: datetime = Factory(utcnow)
    last_updated: datetime = Factory(utcnow)
    dependencies: dict[str, Experiment] = field(eq=False, factory=lambda: {})
    short_slug: str = field()
    slug: str = field()
    tests: list[Test] = Factory(lambda: [])
    artifacts: list[Artifact] = Factory(factory=lambda: [])
    tags: list[str] = Factory(factory=lambda: [])
    dirty: bool = field(eq=False, factory=lambda: True)

    @dir.default
    def _dir_factory(self) -> Path:
        """Get the default directory for the project and the experiment.

        Returns
        -------
        pathlib.Path
            Absolute path to the directory.
        """
        return self.project.parent

    @fs.default
    def _fs_default(self) -> AbstractFileSystem:
        """Define a default local filesystem implementation.

        Returns
        -------
        fsspec.implementations.local.LocalFileSystem
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
            Experiment slug, in the format `{name}-{created_at}`.
        """
        return slugify(f"{self.name}-{self.created_at.strftime('%Y%m%d%H%M%S')}")

    @property
    def path(self) -> Path:
        """Path to an experiment folder.

        This folder can be used to store any plots or artifacts that you want to associate
        with the experiment.

        Returns
        -------
        pathlib.Path
            The path for the experiment.
        """
        return self.dir / self.slug

    def log_metric(self, name: str, value: float | int) -> None:
        """Log a metric to the experiment.

        This method will overwrite existing keys.

        Parameters
        ----------
        name : str
            Name of the metric.
        value : int | float
            Value of the metric.
        """
        self.last_updated = utcnow()
        self.metrics[name] = value

        self.dirty = True

    def log_parameter(self, name: str, value: Any) -> None:
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

    def tag(self, *args: str, overwrite: bool = False) -> None:
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
        fname: str | None = None,
        overwrite: bool = False,
        **kwargs: Any,
    ) -> None:
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
        **kwargs
            Keyword arguments for the write function of the handler.

        Raises
        ------
        lazyscribe.exception.ArtifactLogError
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

    def load_artifact(self, name: str, validate: bool = True, **kwargs: Any) -> Any:
        """Load a single artifact.

        Parameters
        ----------
        name : str
            The name of the artifact to load.
        validate : bool, optional (default True)
            Whether or not to validate the runtime environment against the artifact
            metadata.
        **kwargs
            Keyword arguments for the handler read function.

        Returns
        -------
        Any
            The artifact object.

        Raises
        ------
        lazyscribe.exception.ArtifactLoadError
            If ``validate`` and runtime environment does not match artifact metadata.
            Or if there is no artifact found with the name provided.
        """
        for artifact in self.artifacts:
            if artifact.name == name:
                # Validate the handler
                if validate:
                    validate_artifact_environment(artifact)
                # Read in the artifact
                mode = "rb" if artifact.binary else "r"
                with self.fs.open(str(self.path / artifact.fname), mode) as buf:
                    out = artifact.read(buf, **kwargs)
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
    def log_test(self, name: str, description: str | None = None) -> Iterator[Test]:
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
        lazyscribe.test.Test
            The :py:class:`lazyscribe.test.Test` dataclass.
        """
        test = Test(name=name, description=description)

        yield test

        self.last_updated = utcnow()
        self.tests.append(test)

        self.dirty = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize the experiment to a dictionary.

        Returns
        -------
        dict[str, Any]
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

    def promote_artifact(self, repository: Repository, name: str) -> None:
        """Associate an artifact with a :py:class:`lazyscribe.repository.Repository`.

        The purpose of this method is to move an artifact from an *ephemeral*
        experiment to the versioned repository.

        If the artifact does not exist on disk yet, this function is simply a passthrough
        to :py:meth:`lazyscribe.repository.Repository.log_artifact`. If the artifact does
        exist on disk already, this function will copy the artifact from the experiment
        directory to the repository, increment the version, and call
        :py:meth:`lazyscribe.repository.Repository.save`.

        Parameters
        ----------
        repository : lazyscribe.repository.Repository
            The :py:class:`lazyscribe.repository.Repository` to promote the artifact to.
        name : str
            The artifact to promote.

        Raises
        ------
        lazyscribe.exception.ArtifactLogError
            Raised if the artifact to be promoted is not newer than the latest version available
            in the repository.
            Raised if

            * the artifact ``name`` exists on the filesystem, and
            * the filesystem protocol does not match between the repository and the experiment.
        lazyscribe.exception.ArtifactLoadError
            Raised if there is no artifact with the name ``name`` in the experiment.
        lazyscribe.exception.SaveError
            Raised when writing to the filesystem fails.
        """
        for artifact in self.artifacts:
            if artifact.name == name:
                try:
                    meta_ = repository.get_artifact_metadata(name)
                    if (
                        datetime.strptime(meta_["created_at"], "%Y-%m-%dT%H:%M:%S")
                        >= artifact.created_at
                    ):
                        raise ArtifactLogError(
                            f"Artifact `{name}` is not newer than the latest version available in the repository."
                        ) from None
                    new_handler = evolve(artifact, version=meta_["version"] + 1)
                except ValueError:
                    new_handler = copy(artifact)

                if artifact.dirty:
                    LOG.debug(
                        f"The current value for artifact '{name}' is not on the filesystem."
                    )
                    repository.artifacts.append(new_handler)
                else:
                    # The artifact is on disk, we will have to copy it over
                    curr_path = self.path / artifact.fname
                    if self.fs.protocol != repository.fs.protocol:
                        raise ArtifactLogError(
                            "The repository and the experiment use different filesystems. "
                            f"Please move {curr_path!s} from the experiment filesystem to "
                            "the Repository filesystem and log it manually."
                        )
                    new_path = repository.dir / artifact.name
                    LOG.debug(f"Copying '{curr_path!s}' to '{new_path!s}{os.sep}'")
                    if not self.fs.isdir(f"{new_path!s}{os.sep}"):
                        LOG.debug(f"Creating '{new_path!s}{os.sep}'")
                        self.fs.mkdir(f"{new_path!s}{os.sep}", create_parents=True)
                    self.fs.copy(str(curr_path), f"{new_path!s}{os.sep}")

                    repository.artifacts.append(new_handler)
                    LOG.info(
                        "Calling `save` on the repository since the artifact exists on disk already."
                    )
                    try:
                        repository.save()
                    except SaveError as exc:
                        LOG.info(
                            f"Save failed, deleting '{(new_path / artifact.fname)!s}'..."
                        )
                        self.fs.rm(str(new_path / artifact.fname))
                        del repository.artifacts[-1]

                        raise exc
                break
        else:
            raise ArtifactLoadError(f"No artifact with name {name}")

    def __str__(self) -> str:
        """Shortened string representation."""
        return f"<lazyscribe.experiment.Experiment at {hex(id(self))}>"

    def __gt__(self, other: Experiment) -> bool:
        """Determine whether this experiment is newer than another experiment.

        If the experiments have the same ``slug``, this function will compare using the
        ``last_updated`` attribute. If the ``slug`` is different, this function will use
        the ``created_at`` value.
        """
        if self.slug == other.slug:
            return self.last_updated > other.last_updated
        else:
            return self.created_at > other.created_at

    def __lt__(self, other: Experiment) -> bool:
        """Determine whether this experiment is older than another experiment.

        If the experiments have the same ``slug``, this function will compare using the
        ``last_updated`` attribute. If the ``slug`` is different, this function will use
        the ``created_at`` value.
        """
        if self.slug == other.slug:
            return self.last_updated < other.last_updated
        else:
            return self.created_at < other.created_at

    def __ge__(self, other: Experiment) -> bool:
        """Determine whether this experiment is newer than another experiment.

        If the experiments have the same ``slug``, this function will compare using the
        ``last_updated`` attribute. If the ``slug`` is different, this function will use
        the ``created_at`` value.
        """
        return bool(self == other or self > other)

    def __le__(self, other: Experiment) -> bool:
        """Determine whether this experiment is older than another experiment.

        If the experiments have the same ``slug``, this function will compare using the
        ``last_updated`` attribute. If the ``slug`` is different, this function will use
        the ``created_at`` value.
        """
        return bool(self == other or self < other)


@frozen
class ReadOnlyExperiment(Experiment):
    """Immutable version of an experiment."""

    def __str__(self) -> str:
        """Shortened string representation."""
        return f"<lazyscribe.experiment.ReadOnlyExperiment at {hex(id(self))}>"
