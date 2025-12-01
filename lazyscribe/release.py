"""Repository releases."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from io import IOBase
from typing import Any, Literal

from attrs import Factory, define, field

from lazyscribe._utils import utcnow
from lazyscribe.repository import Repository

LOG = logging.getLogger(__name__)


@define
class Release:
    """Create a release associated with a Repository instance.

    Parameters
    ----------
    tag : str
        A string descriptor for the release. Commonly coincides with semantic
        or calendar versioning.
    artifacts : list[tuple[str, int]]
        A list of the latest available artifacts and versions in the source repository.
    created_at : datetime.datetime, optional (default ``lazyscribe._utils.utcnow()``)
        The creation timestamp for the release (in UTC).
    """

    tag: str = field()
    artifacts: list[tuple[str, int]] = field()
    created_at: datetime = Factory(utcnow)

    def to_dict(self) -> dict[str, list[tuple[str, int]] | str]:
        """Serialize the release to a dictionary.

        Returns
        -------
        dict
            A dictionary with the release information.
        """
        return {
            "tag": self.tag,
            "artifacts": self.artifacts,
            "created_at": self.created_at.isoformat(timespec="seconds"),
        }

    @classmethod
    def from_dict(cls, info: dict[str, Any]) -> Release:
        """Convert a serialized representation of the release back to a python object.

        Parameters
        ----------
        info : dict
            The dictionary representation of the release.

        Returns
        -------
        lazyscribe.release.Release
            The new release object.
        """
        return cls(
            tag=info["tag"],
            artifacts=info["artifacts"],
            created_at=datetime.fromisoformat(info["created_at"]),
        )


def create_release(repository: Repository, tag: str) -> Release:
    """Create a release.

    A release is a collection of specific artifact versions. It is generated
    by taking the latest available version of each artifact.

    Parameters
    ----------
    repository : lazyscribe.repository.Repository
        The source repository.
    tag : str
        A string descriptor of the tag. Commonly coincides with semantic or calendar
        versioning.

    Returns
    -------
    lazyscribe.release.Release
        The release object.
    """
    if repository.mode != "r":
        raise RuntimeError("Repository must be in read-only mode for filtering.")
    if any(art.dirty for art in repository.artifacts):
        raise RuntimeError(
            "At least one artifact has changed since it was last saved. Please save your "
            "repository and re-open it in read-only mode before filtering."
        )

    all_artifacts_ = sorted({art.name for art in repository.artifacts})
    latest: list[tuple[str, int]] = []
    for name in all_artifacts_:
        art = repository._search_artifact_versions(name)
        latest.append((name, art.version))

    return Release(tag=tag, artifacts=latest)


def find_release(
    releases: list[Release],
    version: str | datetime | None = None,
    match: Literal["asof", "exact"] = "exact",
) -> Release:
    """Find a release based on tag or timestamp.

    Parameters
    ----------
    releases : list[lazyscribe.release.Release]
        The releases associated with the repository.
    version : str | datetime, optional (default None)
        The version to find. If a string is provided, the function will assume
        the value corresponds to a ``tag``. If a datetime is provided, the function
        will assume the value corresponds to a creation date. If None is provided,
        the latest release will be returned.
    match : {"asof", "exact"}, optional (default "exact")
        Matching logic. Only relevant if a datetime is provided for ``version``.
        ``exact`` will provide the release with the exact value matching ``version``.
        ``asof`` will provide the most recent release as of the ``version`` datetime
        provided.

    Returns
    -------
    lazyscribe.release.Release
        The release object.

    Raises
    ------
    ValueError
        Raised if the ``tag`` or ``created_at`` cannot be found with the given
        matching logic.
    """
    out: Release

    releases_ = sorted(releases, key=lambda x: x.created_at)
    match (match, version):
        case (_, None):
            out = releases_[-1]
        case ("exact", str() as tag):
            try:
                out = next(ver for ver in releases_ if ver.tag == tag)
            except StopIteration:
                msg = f"Cannot find release with tag '{tag}'"
                raise ValueError(msg) from None
        case ("exact", datetime() as created_at):
            try:
                out = next(ver for ver in releases_ if ver.created_at == created_at)
            except StopIteration:
                msg = f"Cannot find release with creation date of {created_at!s}"
                raise ValueError(msg) from None
        case ("asof", str()):
            raise ValueError(
                "Cannot perform an ``asof`` match using a tag. Please provide a "
                "``datetime.datetime`` value to perform an ``asof`` match."
            )
        case ("asof", datetime() as created_at):
            if created_at < releases_[0].created_at:
                msg = (
                    f"Creation date {created_at!s} predates the earliest release: "
                    f"'{releases_[0].tag}' ({releases_[0].created_at!s})"
                )
                raise ValueError(msg)
            try:
                out = next(
                    ver
                    for idx, ver in enumerate(releases_)
                    if (
                        created_at >= ver.created_at
                        and created_at < releases_[idx + 1].created_at
                    )
                )
            except IndexError:
                out = releases_[-1]
        case _:
            msg = "Invalid parameterization. Please provide ``exact`` or ``asof`` for ``match``."
            raise ValueError(msg)

    LOG.info(f"Found release '{out.tag}' ({out.created_at!s})")

    return out


def dump(obj: list[Release], fp: IOBase, **kwargs: Any) -> None:
    """Write the releases data.

    .. code-block:: python

        from lazyscribe import release as lzr

        releases: list[lazyscribe.release.Release]
        with open("releases.json", "w") as outfile:
            lzr.dump(releases, outfile)

    Parameters
    ----------
    obj : list[lazyscribe.release.Release]
        The list of release objects.
    fp : io.IOBase
        A buffer we can write to.
    **kwargs
        Keyword arguments for ``json.dump``.
    """
    json.dump([ver.to_dict() for ver in obj], fp, **kwargs)


def dumps(obj: list[Release], **kwargs: Any) -> str:
    """Convert a list of releases to a JSON-serialized string.

    To prevent namespace confusion, we recommend importing this function
    through an alias:

    .. code-block:: python

        from lazyscribe import release as lzr

        releases: list[lzr.Release]
        out = lzr.dumps(releases)

    Parameters
    ----------
    obj : list[lazyscribe.release.Release]
        The list of release objects.
    **kwargs
        Keyword arguments for ``json.dumps``.

    Returns
    -------
    str
        The JSON-serialized string.
    """
    return json.dumps([ver.to_dict() for ver in obj], **kwargs)


def load(fp: IOBase, **kwargs: Any) -> list[Release]:
    """Generate a list of releases from a file buffer.

    To prevent namespace confusion, we recommend importing this function
    through an alias:

    .. code-block:: python

        from lazyscribe import release as lzr

        with open("releases.json") as infile:
            releases = lzr.load(infile)

    Parameters
    ----------
    fp : file-like object
        A buffer that we can read using JSON.
    **kwargs
        Keyword arguments for ``json.load``

    Returns
    -------
    list[lazyscribe.release.Release]
        A list of releases.
    """
    json_data_ = json.load(fp, **kwargs)

    return [Release.from_dict(ver) for ver in json_data_]


def loads(s: str, **kwargs: Any) -> list[Release]:
    """Generate a list of releases from a string.

    To prevent namespace confusion, we recommend importing this module
    through an alias:

    .. code-block:: python

        from lazyscribe import release as lzr

        mydata = '[{"tag": "v0.1.0", "artifacts": [], "created_at": "2025-01-01T00:00:00"}]'
        releases = lzr.loads(mydata)

    Parameters
    ----------
    s : str
        The string representation of a JSON file.
    **kwargs
        Keyword arguments for ``json.loads``

    Returns
    -------
    list[lazyscribe.release.Release]
        A list of releases.
    """
    json_data_ = json.loads(s, **kwargs)

    return [Release.from_dict(ver) for ver in json_data_]
