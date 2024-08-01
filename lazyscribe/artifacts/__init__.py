"""Import the handlers."""

from importlib import import_module
from typing import List, Type, Union

from importlib_metadata import entry_points

from lazyscribe.artifacts.base import Artifact

__all__: List[str] = ["_get_handler"]


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
    # for obj in Artifact.__subclasses__():
    #     if obj.alias == alias:
    #         out = obj
    #         break
    # else:
    #     raise ValueError(f"No handler available with the alias {alias}")

    # return out

    eps = entry_points()
    entry = eps.select(group="artifact_type")

    for full_artifact_class in entry:
        if full_artifact_class.name == alias:
            mod, name = full_artifact_class.value.rsplit(".", 1)
            try:
                mod = import_module(mod)
            except ImportError as imp:
                raise RuntimeError(
                    f"Unable to import handler for {alias} through entry points or standard import."
                ) from imp
            
            for part in name.split("."):
                mod = getattr(mod, part)
            
            if not isinstance(mod, type):
                raise TypeError(f"{full_artifact_class} is not a class")
            
            break
    
    else:
        raise ValueError(f"No handler available with the alias {alias}")

    return mod
