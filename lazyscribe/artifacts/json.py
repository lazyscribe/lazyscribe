"""Artifact handler for JSON-serializable objects."""

from json import dump, load
from typing import ClassVar

from attrs import define

from .base import Artifact


@define(auto_attribs=True)
class JSONArtifact(Artifact):
    """Handler for JSON-serializable objects."""

    alias: ClassVar[str] = "json"
    binary: ClassVar[bool] = False

    @classmethod
    def construct(cls):
        """Construct the handler class.

        Included for compatibility.
        """
        return cls()

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
