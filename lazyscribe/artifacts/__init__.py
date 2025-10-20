"""Import the handlers."""

from importlib.metadata import entry_points

from lazyscribe.artifacts.base import Artifact

__all__: list[str] = ["_get_handler"]


def _get_handler(alias: str) -> type[Artifact]:
    """Retrieve a specific handler based on the alias.

    Parameters
    ----------
    alias : str
        The alias for the handler.

    Returns
    -------
    type[lazyscribe.artifacts.base.Artifact]
        The artifact handler class.
    """
    entry = entry_points(group="lazyscribe.artifact_type")

    for full_artifact_class in entry:  # search through entrypoints first
        if full_artifact_class.name == alias:
            try:
                mod = full_artifact_class.load()
            except ImportError as imp:
                raise ImportError(
                    f"Unable to import handler for {alias} through entry points"
                ) from imp

            if not isinstance(mod, type):
                raise TypeError(f"{full_artifact_class} is not a class")

            break

    else:
        for obj in Artifact.__subclasses__():  # search through experiment subclasses
            if obj.alias == alias:
                mod = obj
                break

        # no handler found in both entrypoints or subclass
        else:
            raise ValueError(
                f"No handler available with the name {alias} in `artifact_type` group."
            )

    return mod  # type: ignore
