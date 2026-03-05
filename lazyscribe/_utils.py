"""Util methods."""

import inspect
import json
import warnings
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attrs import Attribute, asdict, fields, filters
from fsspec.spec import AbstractFileSystem

from lazyscribe.artifacts.base import Artifact
from lazyscribe.exception import ArtifactLoadError
from lazyscribe.registry import registry


def serializer(inst: type, field: "Attribute[Any]", value: Any) -> Any:
    """Datetime and dependencies converter for :meth:`attrs.asdict`.

    Parameters
    ----------
    inst : type
        Included for compatibility.
    field : attrs.Attribute[Any]
        The field name.
    value : Any
        The field value.

    Returns
    -------
    Any
        Converted value for easy serialization.
    """
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if field is not None and field.name == "dependencies":
        deps: list[str] = []
        for exp in value.values():
            if (project := registry.search(exp.project)) is not None:
                deps.append(f"{project}|{exp.slug}")
            else:
                deps.append(f"{exp.project}|{exp.slug}")
        return deps
    if field is not None and field.name == "tests":
        tests: list[dict[str, Any]] = [test.to_dict() for test in value]
        return tests
    if field is not None and field.name == "artifacts":
        art: list[dict[str, Any]] = list(serialize_artifacts(value))
        return art

    return value


def serialize_artifacts(alist: list[Artifact]) -> Iterator[dict[str, Any]]:
    """Serialize list of artifacts."""
    yield from (
        {
            **asdict(
                artifact,
                filter=filters.exclude(
                    fields(type(artifact)).value,
                    fields(type(artifact)).writer_kwargs,
                    fields(type(artifact)).dirty,
                ),
                value_serializer=lambda _, __, value: (
                    value.isoformat(timespec="seconds")
                    if isinstance(value, datetime)
                    else value
                ),
            ),
            "handler": artifact.alias,
        }
        for artifact in alist
    )


def utcnow() -> datetime:
    """Return the naive datetime now in UTC.

    Returns
    -------
    datetime.datetime
        Now in UTC, without timezone info.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def load_artifact_from(
    artifacts: list[Artifact],
    path: Path,
    fs: AbstractFileSystem,
    name: str,
    validate: bool = True,
    **kwargs: Any,
) -> Any:
    """Load a single artifact by name.

    Parameters
    ----------
    artifacts : list[Artifact]
        The list of artifacts to search.
    path : Path
        The base path for artifact files.
    fs : AbstractFileSystem
        The filesystem to use for reading.
    name : str
        The name of the artifact to load.
    validate : bool, optional (default True)
        Whether or not to validate the runtime environment against the artifact
        metadata.
    **kwargs
        Keyword arguments for the handler read function.

    Returns
    -------
    Any
        The artifact object.

    Raises
    ------
    lazyscribe.exception.ArtifactLoadError
        If ``validate`` and runtime environment does not match artifact metadata.
        Or if there is no artifact found with the name provided.
    """
    for artifact in artifacts:
        if artifact.name == name:
            if validate:
                validate_artifact_environment(artifact)
            mode = "rb" if artifact.binary else "r"
            with fs.open(str(path / artifact.fname), mode) as buf:
                out = artifact.read(buf, **kwargs)
            if artifact.output_only:
                warnings.warn(
                    f"Artifact '{name}' is not the original Python Object",
                    UserWarning,
                    stacklevel=3,
                )
            return out
    raise ArtifactLoadError(f"No artifact with name {name}")


def validate_artifact_environment(artifact: Artifact) -> None:
    """Validate the artifact handler environment.

    Parameters
    ----------
    artifact : Artifact
        An artifact handler instantiated from project and/or repository metadata.

    Raises
    ------
    lazyscribe.exception.ArtifactLoadError
        Raised if the runtime environment does not match artifact metadata.
    """
    # Construct the handler with relevant parameters.
    artifact_attrs: dict[str, Any] = {
        x: y
        for x, y in inspect.getmembers(artifact)
        if not x.startswith("_") and not inspect.ismethod(y)
    }
    # Exclude parameters that don't define equality
    exclude_names: list[str] = [
        attr.name for attr in fields(type(artifact)) if not attr.eq
    ]
    construct_params: list[str] = [
        param_name
        for param_name, param in inspect.signature(
            artifact.construct
        ).parameters.items()
        if param_name not in exclude_names or param.default == param.empty
    ]
    artifact_attrs = {
        key: value for key, value in artifact_attrs.items() if key in construct_params
    }

    curr_handler = type(artifact).construct(**artifact_attrs, dirty=False)
    # Validate the handler
    if curr_handler != artifact:
        field_filters = filters.exclude(
            *[attr for attr in fields(type(artifact)) if not attr.eq]
        )
        raise ArtifactLoadError(
            "Runtime environments do not match. Artifact parameters:\n\n"
            f"{json.dumps(asdict(artifact, filter=field_filters))}"
            "\n\nCurrent parameters:\n\n"
            f"{json.dumps(asdict(curr_handler, filter=field_filters))}"
        )
