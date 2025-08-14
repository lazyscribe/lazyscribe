"""PyYAML-based handler for YAML-serializable artifacts."""

from __future__ import annotations

import logging
from datetime import datetime
from io import IOBase
from typing import Any, ClassVar

import yaml

from lazyscribe._utils import utcnow

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:  # pragma: no cover
    from yaml import SafeLoader  # type: ignore[assignment]
from attrs import define
from slugify import slugify

from lazyscribe.artifacts.base import Artifact

LOG = logging.getLogger(__name__)


@define(auto_attribs=True)
class YAMLArtifact(Artifact):
    """Handler for YAML-serializable objects.

    .. important::

        This class is not meant to be initialized directly. Please use the ``construct``
        method.

    .. note::

        For the attributes documentation, see also "Attributes" of :py:class:`lazyscribe.artifacts.base.Artifact`.

    Attributes
    ----------
    alias : str = "yaml"
    suffix : str = "yaml"
    binary : bool = False
    output_only : bool = False
    """

    alias: ClassVar[str] = "yaml"
    suffix: ClassVar[str] = "yaml"
    binary: ClassVar[bool] = False
    output_only: ClassVar[bool] = False

    @classmethod
    def construct(
        cls,
        name: str,
        value: Any = None,
        fname: str | None = None,
        created_at: datetime | None = None,
        writer_kwargs: dict[str, Any] | None = None,
        version: int = 0,
        dirty: bool = True,
        **kwargs: Any,
    ) -> YAMLArtifact:
        """Construct the handler class.

        Parameters
        ----------
        name : str
            The name of the artifact.
        value : Any, optional (default None)
            The value for the artifact. The default value of ``None`` is used when
            an experiment is loaded from the project JSON.
        fname : str, optional (default None)
            The filename for the artifact. If set to ``None`` or not provided, it will be derived from
            the name of the artifact and the suffix for the class.
        created_at : datetime.datetime, optional (default ``lazyscribe._utils.utcnow()``)
            When the artifact was created.
        writer_kwargs : dict[str, Any], optional (default {})
            Keyword arguments for writing an artifact to the filesystem. Provided when an artifact
            is logged to an experiment.
        version : int, optional (default 0)
            Integer version to be used for versioning artifacts.

        Returns
        -------
        YAMLArtifact
            The artifact.
        """
        created_at = created_at or utcnow()
        return cls(
            name=name,
            value=value,
            fname=fname
            or f"{slugify(name)}-{slugify(created_at.strftime('%Y%m%d%H%M%S'))}.{cls.suffix}",
            created_at=created_at,
            writer_kwargs=writer_kwargs or {},
            version=version,
            dirty=dirty,
        )

    @classmethod
    def read(cls, buf: IOBase, **kwargs: Any) -> Any:
        """Read in the artifact.

        Parameters
        ----------
        buf : file-like object
            The buffer from a ``fsspec`` filesystem.
        **kwargs
            Keyword arguments for the read method.

        Returns
        -------
        Any
            The artifact object.
        """
        if "Loader" not in kwargs:
            LOG.debug("No loader provided, defaulting to SafeLoader")
            kwargs["Loader"] = SafeLoader  # default to safe loader

        return yaml.load(buf, **kwargs)

    @classmethod
    def write(cls, obj: Any, buf: IOBase, **kwargs: Any) -> None:
        """Write the content to a YAML file.

        Parameters
        ----------
        obj : Any
            The YAML-serializable object.
        buf : file-like object
            The buffer from a ``fsspec`` filesystem.
        **kwargs
            Keyword arguments for :py:meth:`yaml.dump`.
        """
        yaml.dump(obj, buf, **kwargs)
