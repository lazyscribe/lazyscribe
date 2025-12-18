"""Pickle-based handler for binary artifacts."""

from __future__ import annotations

import logging
import pickle
import sys
from datetime import datetime
from io import IOBase
from typing import Any, ClassVar

from attrs import define, field
from slugify import slugify

from lazyscribe._utils import utcnow
from lazyscribe.artifacts.base import Artifact

LOG = logging.getLogger(__name__)


@define(auto_attribs=True)
class PickleArtifact(Artifact):
    """Pickle-based serialization for python objects.

    .. important::

        This class is not meant to be initialized directly. Please use the ``construct``
        method.

    .. note::

        For the attributes documentation, please see the "Attributes" section of
        :py:class:`lazyscribe.artifacts.base.Artifact`.

    Attributes
    ----------
    alias : str = "pickle"
    suffix : str = "pkl"
    binary : bool = False
    output_only : bool = False

    python_version : str
        Minor Python version (e.g. ``"3.10"``).
    """

    alias: ClassVar[str] = "pickle"
    suffix: ClassVar[str] = "pkl"
    binary: ClassVar[bool] = True
    output_only: ClassVar[bool] = False
    python_version: str = field()

    @classmethod
    def construct(
        cls,
        name: str,
        value: Any = None,
        fname: str | None = None,
        created_at: datetime | None = None,
        expiry: datetime | None = None,
        writer_kwargs: dict[str, Any] | None = None,
        version: int = 0,
        dirty: bool = True,
        **kwargs: Any,
    ) -> PickleArtifact:
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
        expiry : datetime.datetime, optional (default None)
            When the artifact expired.
        writer_kwargs : dict[str, Any], optional (default {})
            Keyword arguments for writing an artifact to the filesystem. Provided when an artifact
            is logged to an experiment.
        version : int, optional (default 0)
            Integer version to be used for versioning artifacts.
        dirty : bool, optional (default True)
            Whether or not this artifact should be saved when :py:meth:`lazyscribe.project.Project.save`
            or :py:meth:`lazyscribe.repository.Repository.save` is called. This decision is based
            on whether the artifact is new or has been updated.
        python_version : str, optional
            Minor Python version (e.g. ``"3.10"``).

        Returns
        -------
        JSONArtifact
            The artifact.
        """
        python_version = kwargs.get("python_version") or ".".join(
            str(i) for i in sys.version_info[:2]
        )
        created_at = created_at or utcnow()
        return cls(
            name=name,
            value=value,
            fname=fname
            or f"{slugify(name)}-{slugify(created_at.strftime('%Y%m%d%H%M%S'))}.{cls.suffix}",
            created_at=created_at,
            expiry=expiry,
            writer_kwargs=writer_kwargs or {},
            version=version,
            dirty=dirty,
            python_version=python_version,
        )

    @classmethod
    def read(cls, buf: IOBase, **kwargs: Any) -> Any:
        """Read in the file.

        Parameters
        ----------
        buf : file-like object
            The buffer from a ``fsspec`` filesystem.
        **kwargs
            Keyword arguments for :py:meth:`pickle.load`.

        Returns
        -------
        Any
            The deserialized Python object.
        """
        return pickle.load(buf, **kwargs)

    @classmethod
    def write(cls, obj: Any, buf: IOBase, **kwargs: Any) -> None:
        """Write the content to a pickle file.

        Parameters
        ----------
        obj : object
            The serializable object.
        buf : file-like object
            The buffer from a ``fsspec`` filesystem.
        **kwargs
            Keyword arguments for :py:meth:`pickle.dump`.
        """
        pickle.dump(obj, buf, **kwargs)
