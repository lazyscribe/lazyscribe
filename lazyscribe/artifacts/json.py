"""Artifact handler for JSON-serializable objects."""

from __future__ import annotations

import sys
from datetime import datetime
from json import dump, load
from typing import Any, ClassVar

from attrs import define
from slugify import slugify

from lazyscribe._utils import utcnow
from lazyscribe.artifacts.base import Artifact


@define(auto_attribs=True)
class JSONArtifact(Artifact):
    """Handler for JSON-serializable objects.

    .. important::

        This class is not meant to be initialized directly. Please use the ``construct``
        method.
    """

    alias: ClassVar[str] = "json"
    suffix: ClassVar[str] = "json"
    binary: ClassVar[bool] = False
    output_only: ClassVar[bool] = False
    python_version: str

    @classmethod
    def construct(
        cls,
        name: str,
        value: Any = None,
        fname: str | None = None,
        created_at: datetime | None = None,
        writer_kwargs: dict | None = None,
        version: int = 0,
        dirty: bool = True,
        **kwargs,
    ):
        """Construct the handler class.

        Parameters
        ----------
        name : str
            The name of the artifact.
        value : object, optional (default None)
            The value for the artifact. The default value of ``None`` is used when
            an experiment is loaded from the project JSON.
        fname : str, optional (default None)
            The filename of the artifact. If not provided, this value will be derived from
            the name of the artifact and the suffix for the class.
        created_at : datetime, optional (default None)
            When the artifact was created. If not supplied, :py:meth:`datetime.now` will be used.
        writer_kwargs : dict, optional (default None)
            Keyword arguments for writing an artifact to the filesystem. Provided when an artifact
            is logged to an experiment.
        version : int, optional (default 0)
            Integer version to be used for versioning artifacts.
        dirty : bool, optional (default True)
            Whether or not this artifact should be saved when :py:meth:`lazyscribe.project.Project.save`
            or :py:meth:`lazyscribe.repository.Repository.save` is called. This decision is based
            on whether the artifact is new or has been updated.
        **kwargs : dict
            Other keyword arguments.
            Usually class attributes obtained from a project JSON.
        """
        python_version = kwargs.get("python_version") or ".".join(
            str(i) for i in sys.version_info[:2]
        )
        created_at = created_at or utcnow()
        return cls(
            name=name,
            value=value,
            writer_kwargs=writer_kwargs or {},
            fname=fname
            or f"{slugify(name)}-{slugify(created_at.strftime('%Y%m%d%H%M%S'))}.{cls.suffix}",
            created_at=created_at,
            python_version=python_version,
            version=version,
            dirty=dirty,
        )

    @classmethod
    def read(cls, buf, **kwargs):
        """Read in the JSON file.

        Parameters
        ----------
        buf : file-like object
            The buffer from a ``fsspec`` filesystem.
        **kwargs : dict
            Keyword arguments for :py:meth:`json.load`

        Returns
        -------
        Any
            The deserialized JSON file.
        """
        return load(buf, **kwargs)

    @classmethod
    def write(cls, obj, buf, **kwargs):
        """Write the content to a JSON file.

        Parameters
        ----------
        obj : object
            The JSON-serializable object.
        buf : file-like object
            The buffer from a ``fsspec`` filesystem.
        **kwargs : dict
            Keyword arguments for :py:meth:`json.dump`.
        """
        dump(obj, buf, **kwargs)
