"""Util methods."""

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from attrs import Attribute, asdict, fields, filters

from lazyscribe.artifacts.base import Artifact


def serializer(inst: type, field: Attribute, value: Any) -> Any:
    """Datetime and dependencies converter for :meth:`attrs.asdict`.

    Parameters
    ----------
    inst
        Included for compatibility.
    field
        The field name.
    value
        The field value.

    Returns
    -------
    Any
        Converted value for easy serialization.
    """
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if field is not None and field.name == "dependencies":
        deps: list[str] = [f"{exp.project}|{exp.slug}" for exp in value.values()]
        return deps
    if field is not None and field.name == "tests":
        tests: list[dict[str, Any]] = [asdict(test) for test in value]
        return tests
    if field is not None and field.name == "artifacts":
        art: list[dict[str, Any]] = list(serialize_artifacts(value))
        return art

    return value


def serialize_artifacts(alist: list[Artifact]) -> Iterator[dict[str, Any]]:
    yield from (
        {
            **asdict(
                artifact,
                filter=filters.exclude(
                    fields(type(artifact)).value,
                    fields(type(artifact)).writer_kwargs,
                    fields(type(artifact)).dirty,
                ),
                value_serializer=lambda _, __, value: value.isoformat(
                    timespec="seconds"
                )
                if isinstance(value, datetime)
                else value,
            ),
            "handler": artifact.alias,
        }
        for artifact in alist
    )


def utcnow() -> datetime:
    """Return the naive datetime now in UTC.

    Returns
    -------
    datetime
        Now in UTC, without timezone info.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
