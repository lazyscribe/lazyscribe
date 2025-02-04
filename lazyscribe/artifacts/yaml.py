
from datetime import datetime
from typing import Any, ClassVar, Literal, Optional
import yaml

try:
    from yaml import CSafeLoader as SafeLoader
    from yaml import CFullLoader as FullLoader
except ImportError:
    from yaml import SafeLoader
    from yaml import FullLoader
from attrs import define
from slugify import slugify

from lazyscribe.artifacts.base import Artifact

@define(auto_attribs=True)
class YAMLArtifact(Artifact):
    """Handler for YAML artifacts."""

    alias: ClassVar[str] = "yaml"
    suffix: ClassVar[str] = "yaml"
    binary: ClassVar[bool] = False
    output_only: ClassVar[bool] = False
    loader: Literal["safe", "full"]

    @classmethod
    def construct(
        cls,
        name: str,
        value: Any = None,
        fname: str | None = None,
        created_at: datetime | None = None,
        writer_kwargs: dict | None = None,
        version: int = 0,
        **kwargs
    ):
        """Construct the handler class."""
        created_at = created_at or datetime.now(),
        return cls(
            name=name,
            value=value,
            fname=fname or f"{slugify(name)}-{slugify(created_at.strftime('%Y%m%d%H%M%S'))}.{cls.suffix}",
            writer_kwargs=writer_kwargs or {},
            version=version,
            created_at=created_at or datetime.now(),
            loader=kwargs.get("loader") or "safe"
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
        if cls.loader == "safe":
            loader = SafeLoader
        elif cls.loader == "full":
            loader = FullLoader
        else:
            raise ValueError("Loader must be 'safe' or 'full'")
        return yaml.load(buf, Loader=loader, **kwargs)

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