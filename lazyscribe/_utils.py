"""Util methods."""

from datetime import datetime

from attrs import asdict, fields, filters


def serializer(inst, field, value):
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
        new = [f"{exp.project}|{exp.slug}" for exp in value.values()]
        return new
    if field is not None and field.name == "tests":
        new = [asdict(test) for test in value]
        return new
    if field is not None and field.name == "artifacts":
        new = [
            {
                **asdict(
                    artifact,
                    filter=filters.exclude(
                        fields(type(artifact)).value,
                        fields(type(artifact)).writer_kwargs,
                    ),
                    value_serializer=lambda _, __, value: value.isoformat(
                        timespec="seconds"
                    )
                    if isinstance(value, datetime)
                    else value,
                ),
                "handler": artifact.alias,
            }
            for artifact in value
        ]
        return new

    return value
