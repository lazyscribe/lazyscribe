"""Import the handlers."""

from typing import List

from .base import Artifact
from .json import JSONArtifact
from .sklearn import SklearnArtifact

__all__: List[str] = ["Artifact", "JSONArtifact", "SklearnArtifact", "_get_handler"]


def _get_handler(alias: str) -> Artifact:
    """Retrieve a specific handler based on the alias.

    Parameters
    ----------
    alias : str
        The alias for the handler.

    Returns
    -------
    Artifact
        The artifact handler.
    """
    for obj in Artifact.__subclasses__():
        if obj.alias == alias:
            out = obj
            break
    else:
        raise ValueError(f"No handler available with the alias {alias}")

    return out
