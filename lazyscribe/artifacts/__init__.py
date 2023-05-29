"""Import the handlers."""

from typing import List, Type

from .base import Artifact
from .json import JSONArtifact
from .joblib import JoblibArtifact

__all__: List[str] = ["Artifact", "JSONArtifact", "JoblibArtifact", "_get_handler"]


def _get_handler(alias: str) -> Type[Artifact]:
    """Retrieve a specific handler based on the alias.

    Parameters
    ----------
    alias : str
        The alias for the handler.

    Returns
    -------
    Artifact
        The artifact handler class object. This object will need to be constructed
        using :py:meth:`lazyscribe.artifacts.Artifact.construct`.
    """
    for obj in Artifact.__subclasses__():
        if obj.alias == alias:
            out = obj
            break
    else:
        raise ValueError(f"No handler available with the alias {alias}")

    return out
