"""PyYAML-based handler for YAML-serializable artifacts."""

from __future__ import annotations

import logging
from datetime import datetime
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
    """Handler for YAML artifacts."""

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
        writer_kwargs: dict | None = None,
        version: int = 0,
        **kwargs,
    ):
        """Construct the handler class."""
        created_at = created_at or utcnow()
        return cls(
            name=name,
            value=value,
            fname=fname
            or f"{slugify(name)}-{slugify(created_at.strftime('%Y%m%d%H%M%S'))}.{cls.suffix}",
            writer_kwargs=writer_kwargs or {},
            version=version,
            created_at=created_at,
        )

    @classmethod
    def read(cls, buf, **kwargs):
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
            The artifact.
        """
        if "Loader" not in kwargs:
            LOG.debug("No loader provided, defaulting to SafeLoader")
            kwargs["Loader"] = SafeLoader  # default to safe loader
        return yaml.load(buf, **kwargs)

    @classmethod
    def write(cls, obj, buf, **kwargs):
        """Write the content to a YAML file.

        Parameters
        ----------
        obj : object
            The YAML-serializable object.
        buf : file-like object
            The buffer from a ``fsspec`` filesystem.
        **kwargs
            Keyword arguments for :py:meth:`yaml.dump`.
        """
        yaml.dump(obj, buf, **kwargs)
