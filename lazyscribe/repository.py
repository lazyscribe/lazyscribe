"""Repository storing and logging."""

from __future__ import annotations

import copy
import difflib
import json
import logging
import warnings
from bisect import bisect
from collections.abc import Iterator
from datetime import datetime
from operator import attrgetter
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import fsspec

from lazyscribe._utils import serialize_artifacts, utcnow, validate_artifact_environment
from lazyscribe.artifacts import _get_handler
from lazyscribe.artifacts.base import Artifact
from lazyscribe.exception import (
    ArtifactLoadError,
    InvalidVersionError,
    ReadOnlyError,
    SaveError,
    VersionNotFoundError,
)

LOG = logging.getLogger(__name__)


class Repository:
    """Repository class for holding versioned artifacts.

    Parameters
    ----------
    fpath : str | Path, optional (default "repository.json")
        The location of the repository file. If no repository file exists, this will be the location
        of the output JSON file when ``save`` is called.
    mode : {"r", "a", "w", "w+"}, optional (default "w+")
        The mode for opening the repository.

        * ``r``: All artifacts will be loaded. No new artifacts can be logged.
        * ``w``: No existing artifacts will be loaded. Artifacts can be added.
        * ``w+``: All artifacts will be loaded. New artifacts can be added.
    **storage_options
        Storage options to pass to the filesystem initialization. Will be passed to
        :py:meth:`fsspec.filesystem`.

    Attributes
    ----------
    artifacts : list[lazyscribe.artifact.Artifact]
        The list of artifacts in the repository.
    """

    fpath: Path
    mode: Literal["r", "w", "w+"]
    storage_options: dict[str, Any]
    artifacts: list[Artifact]

    def __init__(
        self,
        fpath: str | Path = "repository.json",
        mode: Literal["r", "w", "w+"] = "w+",
        **storage_options: Any,
    ) -> None:
        """Init method.

        Raises
        ------
        ValueError
            Raised on invalid ``mode`` value.
        """
        if isinstance(fpath, str):
            parsed = urlparse(fpath)
            self.fpath = Path(parsed.netloc + parsed.path)
            self.protocol = parsed.scheme or "file"
        else:
            self.fpath = fpath
            self.protocol = "file"
        self.dir = self.fpath.parent
        self.storage_options = storage_options

        self.artifacts: list[Artifact] = []
        self.fs = fsspec.filesystem(self.protocol, **storage_options)

        if mode not in ("r", "w", "w+"):
            raise ValueError("Please provide a valid ``mode`` value.")
        self.mode = mode
        if mode in ("r", "w+") and self.fs.isfile(str(self.fpath)):
            self.load()

    def load(self) -> None:
        """Load existing artifacts."""
        with self.fs.open(str(self.fpath), "r") as infile:
            data = json.load(infile)

        artifacts: list[Artifact] = []
        for artifact in data:
            handler_cls = _get_handler(artifact.pop("handler"))
            created_at = datetime.fromisoformat(artifact.pop("created_at"))
            artifacts.append(
                handler_cls.construct(**artifact, created_at=created_at, dirty=False)
            )
        self.artifacts = artifacts

    def log_artifact(
        self,
        name: str,
        value: Any,
        handler: str,
        fname: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Log an artifact to the repository.

        This method associates an artifact with the repository, but the artifact will
        not be written until :py:meth:`lazyscribe.repository.Repository.save` is called.

        Parameters
        ----------
        name : str
            The name of the artifact.
        value : Any
            The object to persist to the filesystem.
        handler : str
            The name of the handler to use for the object.
        fname : str, optional (default None)
            The filename for the artifact. If set to ``None`` or not provided, it will be derived
            from the name of the artifact and the builtin suffix for each handler.
        **kwargs
            Keyword arguments for the write function of the handler.

        Raises
        ------
        lazyscribe.exception.ReadOnlyError
            If repository is in read-only mode.
        """
        if self.mode == "r":
            raise ReadOnlyError("Repository is in read-only mode.")
        # Retrieve and construct the handler
        self.last_updated = utcnow()
        artifacts_matching_name: list[Artifact] = [
            art for art in self.artifacts if art.name == name
        ]
        version = (
            max(art.version for art in artifacts_matching_name) + 1
            if artifacts_matching_name
            else 0
        )
        handler_cls = _get_handler(handler)
        artifact_handler = handler_cls.construct(
            name=name,
            value=value,
            fname=fname,
            created_at=self.last_updated,
            writer_kwargs=kwargs,
            version=version,
        )
        self.artifacts.append(artifact_handler)
        if handler_cls.output_only:
            warnings.warn(
                f"Artifact '{name}' is added. It is not meant to be read back as Python Object",
                UserWarning,
                stacklevel=2,
            )

    def load_artifact(
        self,
        name: str,
        validate: bool = True,
        version: datetime | str | int | None = None,
        match: Literal["asof", "exact"] = "exact",
        **kwargs: Any,
    ) -> Any:
        """Load a single artifact.

        Parameters
        ----------
        name : str
            The name of the artifact to load.
        validate : bool, optional (default True)
            Whether or not to validate the runtime environment against the artifact
            metadata.
        version : datetime.datetime | str | int, optional (default None)
            The version of the artifact to load.
            Can be provided as a datetime corresponding to the ``created_at`` field,
            a string corresponding to the ``created_at`` field in the format ``"%Y-%m-%dT%H:%M:%S"``
            (e.g. ``"2025-01-25T12:36:22"``), or an integer version.
            If set to ``None`` or not provided, defaults to the most recent version.
        match : {"asof", "exact"}, optional (default "exact")
            Matching logic. Only relevant for ``str`` and ``datetime.datetime`` values for
            ``version``. ``exact`` will provide an artifact with the exact ``created_at``
            value provided. ``asof`` will provide the most recent version as of the
            ``version`` value.

            When using an ``asof`` search, only artifacts with no expiry or an ``expiry``
            datetime set _after_ the provided ``version`` value will be included. When
            ``version=None``, any artifacts that are expired as of
            :py:meth:`lazyscribe._utils.utcnow` will be excluded.
        **kwargs
            Keyword arguments for the handler read function.

        Returns
        -------
        Any
            The artifact object.

        Raises
        ------
        ValueError
            Raised on invalid ``match`` value.
            Raised if no valid artifact was found.
        lazyscribe.exception.ArtifactLoadError
            Raised if ``validate`` and runtime environment does not match artifact metadata.
        """
        # Search for the artifact
        artifact = self._search_artifact_versions(
            name=name, version=version, match=match
        )
        if validate:
            validate_artifact_environment(artifact)

        # Read in the artifact
        mode = "rb" if artifact.binary else "r"
        with self.fs.open(str(self.dir / artifact.name / artifact.fname), mode) as buf:
            out = artifact.read(buf, **kwargs)
        if artifact.output_only:
            warnings.warn(
                f"Artifact '{name}' is not the original Python Object",
                UserWarning,
                stacklevel=2,
            )

        return out

    def set_artifact_expiry(
        self,
        name: str,
        version: datetime | str | int | None = None,
        match: Literal["asof", "exact"] = "exact",
        expiry: datetime | str | None = None,
    ) -> None:
        """Set the expiry date for a given artifact.

        Parameters
        ----------
        name : str
            The name of the artifact.
        version : datetime.datetime | str | int, optional (default None)
            The version of the artifact to load.
            Can be provided as a datetime corresponding to the ``created_at`` field,
            a string corresponding to the ``created_at`` field in the format ``"%Y-%m-%dT%H:%M:%S"``
            (e.g. ``"2025-01-25T12:36:22"``), or an integer version.
            If set to ``None`` or not provided, defaults to the most recent version.
        match : {"asof", "exact"}, optional (default "exact")
            Matching logic. Only relevant for ``str`` and ``datetime.datetime`` values for
            ``version``. ``exact`` will provide an artifact with the exact ``created_at``
            value provided. ``asof`` will provide the most recent version as of the
            ``version`` value.
        expiry : datetime.datetime | str, optional (default None)
            The expiry datetime for the artifact version.

        Raises
        ------
        ValueError
            Raised if the value for ``expiry`` cannot be coerced to a datetime.
        """
        if self.mode == "r":
            raise ReadOnlyError("Repository is in read-only mode.")

        # Search for the artifact
        artifact = self._search_artifact_versions(
            name=name, version=version, match=match
        )
        match expiry:
            case datetime():
                artifact.expiry = expiry
            case str():
                artifact.expiry = datetime.strptime(expiry, "%Y-%m-%dT%H:%M:%S")
            case None:
                artifact.expiry = utcnow()
            case _:
                raise ValueError("Value '%s' cannot be coerced to a datetime", expiry)

    def get_artifact_metadata(
        self,
        name: str,
        version: datetime | str | int | None = None,
        match: Literal["asof", "exact"] = "exact",
    ) -> dict[str, Any]:
        """Retrieve the metadata for an artifact.

        Parameters
        ----------
        name : str
            The name of the artifact to load.
        version : datetime.datetime | str | int, optional (default None)
            The version of the artifact to load.
            Can be provided as a datetime corresponding to the ``created_at`` field,
            a string corresponding to the ``created_at`` field in the format ``"%Y-%m-%dT%H:%M:%S"``
            (e.g. ``"2025-01-25T12:36:22"``), or an integer version.
            If set to ``None`` or not provided, defaults to the most recent version.
        match : {"asof", "exact"}, optional (default "exact")
            Matching logic. Only relevant for ``str`` and ``datetime.datetime`` values for
            ``version``. ``exact`` will provide an artifact with the exact ``created_at``
            value provided. ``asof`` will provide the most recent version as of the
            ``version`` value.

        Returns
        -------
        dict[str, Any]
            The artifact metadata.

        Raises
        ------
        ValueError
            Raised on invalid ``match`` value.
            Raised if no valid artifact was found.
        """
        artifact = self._search_artifact_versions(
            name=name, version=version, match=match
        )

        return next(serialize_artifacts([artifact]))

    def get_version_diff(
        self,
        name: str,
        version: datetime
        | str
        | int
        | tuple[datetime | str | int, datetime | str | int],
        match: Literal["asof", "exact"] = "exact",
    ) -> str:
        """Generate the unified diff between versions of the same artifact.

        Parameters
        ----------
        name : str
            The name of the artifact to compare.
        versions : datetime | str | int | tuple[datetime | str | int, datetime | str | int]
            The versions to compare. If a single version is provided, the artifact will
            be compared to the latest available artifact. A tuple specifies the two versions
            to compare.
        match : {"asof", "exact"}, optional (default "exact")
            Matching logic. Only relevant for ``str`` and ``datetime.datetime`` values.
            ``exact`` will provide an artifact with the exact ``created_at``
            value provided. ``asof`` will provide the most recent version as of the
            ``version`` value.

        Raises
        ------
        lazyscribe.exception.ArtifactLoadError
            Raised if the artifact does not exist on the filesystem yet.
        ValueError
            Raised if the provided artifact(s) represent binary files.

        Returns
        -------
        str
            Concatenated output from :py:meth:`difflib.unified_diff`.
        """
        if not isinstance(version, tuple):
            # Retrieve the specified and the latest version
            versions = [
                self._search_artifact_versions(name, version, match),
                self._search_artifact_versions(name, None, match),
            ]
        else:
            versions = sorted(
                [self._search_artifact_versions(name, ver, match) for ver in version],
                key=lambda x: x.created_at,
            )

        if versions[0] == versions[1]:
            LOG.warning(
                f"Only version '{versions[0].version!s}' was supplied for comparison"
            )

        raw_version_data = []
        for art in versions:
            if art.dirty:
                msg = (
                    "Artifact version not found on the filesystem. Please call"
                    " `Repository.save` before calling this method."
                )
                raise ArtifactLoadError(msg)
            if art.binary:
                msg = (
                    f"Version {version} of '{name}' is written to the filesystem "
                    f"using binary handler '{art.alias}'. Binary file formats cannot"
                    "be compared using diffs."
                )
                raise ValueError(msg)
            with self.fs.open(str(self.dir / art.name / art.fname), "r") as buf:
                raw_version_data.append(buf.read().splitlines())

        return "\n".join(list(difflib.unified_diff(*raw_version_data)))

    def save(self) -> None:
        """Save the repository data.

        This includes saving any artifact data.

        Raises
        ------
        lazyscribe.exception.ReadOnlyError
            Raised when trying to save when the project is in read-only mode.
        lazyscribe.exception.SaveError
            Raised when writing to the filesystem fails.
        """
        if self.mode == "r":
            raise ReadOnlyError("Repository is in read-only mode.")

        data = list(self)
        with self.fs.transaction:
            try:
                self.fs.makedirs(str(self.fpath.parent), exist_ok=True)
                with self.fs.open(str(self.fpath), "w") as outfile:
                    json.dump(data, outfile, sort_keys=True, indent=4)
            except Exception as exc:
                raise SaveError(
                    f"Unable to save the Repository JSON file to {self.fpath!s}"
                ) from exc

            for artifact in self.artifacts:
                # Write the artifact data
                fmode = "wb" if artifact.binary else "w"
                artifact_dir = self.dir / artifact.name
                fpath = artifact_dir / artifact.fname
                if not artifact.dirty:
                    LOG.debug(
                        f"Artifact {artifact.name} v{artifact.version} already exists and has not been updated"
                    )
                    continue

                try:
                    self.fs.makedirs(str(artifact_dir), exist_ok=True)
                    LOG.debug(f"Saving '{artifact.name}' to {fpath!s}...")
                    with self.fs.open(str(fpath), fmode) as buf:
                        artifact.write(artifact.value, buf, **artifact.writer_kwargs)
                except Exception as exc:
                    raise SaveError(
                        f"Unable to write '{artifact.name}' to '{fpath!s}'"
                    ) from exc

                # Reset the `dirty` flag since we have the updated artifact on disk
                artifact.dirty = False
                if artifact.output_only:
                    warnings.warn(
                        f"Artifact '{artifact.name}' is added. It is not meant to be read back as Python Object",
                        UserWarning,
                        stacklevel=2,
                    )

    def filter(
        self, version: datetime | str | list[tuple[str, datetime | str | int]]
    ) -> Repository:
        """Filter a repository.

        This method returns a new, read-only object with a subset of the input artifacts.
        Use this method to truncate a repository to a collection of artifacts relevant to
        a given use case.

        Parameters
        ----------
        version : datetime.datetime | str | list[tuple[str, datetime.datetime | str | int]]
            The version corresponding to the output version of each artifact. If a datetime
            or string is provided, this method will do an ``asof`` search for each artifact.

            If a list is provided, it will be treated as a list of exact versions to load.

        Returns
        -------
        lazyscribe.repository.Repository
            A read-only copy of the existing repository with one version per artifact.

        Raises
        ------
        RuntimeError
            Raised if the current repository object has artifacts that have not been saved
            to the filesystem.
        """
        if self.mode != "r":
            raise RuntimeError("Repository must be in read-only mode for filtering.")
        if any(art.dirty for art in self.artifacts):
            raise RuntimeError(
                "At least one artifact has changed since it was last saved. Please save your "
                "repository and re-open it in read-only mode before filtering."
            )

        new_ = copy.copy(self)
        all_artifacts_ = {art.name for art in new_.artifacts}

        new_.artifacts = []
        match version:
            case datetime() | str():
                for art in all_artifacts_:
                    try:
                        latest = self._search_artifact_versions(
                            name=art, version=version, match="asof"
                        )
                        new_.artifacts.append(latest)
                    except VersionNotFoundError:
                        LOG.warning(
                            f"Artifact '{art}' does not have a version that predates {version!s}"
                        )
            case list():
                for art, ver in version:
                    new_.artifacts.append(
                        self._search_artifact_versions(
                            name=art, version=ver, match="exact"
                        )
                    )

        return new_

    def _search_artifact_versions(
        self,
        name: str,
        version: datetime | str | int | None = None,
        match: Literal["asof", "exact"] = "exact",
    ) -> Artifact:
        """Search for an artifact based on name and version.

        Parameters
        ----------
        name : str
            The name of the artifact to load.
        version : datetime.datetime | str | int, optional (default None)
            The version of the artifact to load.
            Can be provided as a datetime corresponding to the ``created_at`` field,
            a string corresponding to the ``created_at`` field in the format ``"%Y-%m-%dT%H:%M:%S"``
            (e.g. ``"2025-01-25T12:36:22"``), or an integer version.
            If set to ``None`` or not provided, defaults to the most recent version.
        match : {"asof", "exact"}, optional (default "exact")
            Matching logic. Only relevant for ``str`` and ``datetime.datetime`` values for
            ``version``. ``exact`` will provide an artifact with the exact ``created_at``
            value provided. ``asof`` will provide the most recent version as of the
            ``version`` value.

        Raises
        ------
        ValueError
            Raised if there are no artifacts with the provided name.
            Raised if ``match`` is an invalid value.
        VersionNotFoundError
            Raised if the version cannot be found.
        InvalidVersionError
            Raised if the version cannot be coerced. Only relevant for string values.
        """
        artifacts_matching_name = sorted(
            [art for art in self.artifacts if art.name == name],
            key=lambda x: x.created_at,
        )
        if not artifacts_matching_name:
            raise ValueError(f"No artifact with name {name}")
        try:
            version = (
                datetime.strptime(version, "%Y-%m-%dT%H:%M:%S")
                if isinstance(version, str)
                else version
            )
        except ValueError as exc:
            msg = f"Invalid version identifier provided. {version} is not in the format YYYY-MM-DDTHH:MM:SS"
            raise InvalidVersionError(msg) from exc

        match (match, version):
            case (_, None):
                today = utcnow()
                best_before_ = [
                    art
                    for art in artifacts_matching_name
                    if art.expiry is None or today < art.expiry
                ]
                try:
                    artifact = best_before_[-1]
                except IndexError as exc:
                    msg = (
                        f"Using {today!s} as a reference, all artifacts with "
                        f"the name '{name}' are expired."
                    )
                    raise VersionNotFoundError(msg) from exc
            case ("exact", datetime()):
                try:
                    artifact = next(
                        art
                        for art in artifacts_matching_name
                        if art.created_at == version
                    )
                except StopIteration:
                    raise VersionNotFoundError(
                        f"No artifact named {name} with version {version}"
                    ) from None
            case ("asof", datetime()):
                LOG.info(
                    f"Searching for the latest version of '{name}' as of {version!s}..."
                )

                eligible_idx_ = bisect(
                    artifacts_matching_name, version, key=attrgetter("created_at")
                )
                eligible_artifacts_ = artifacts_matching_name[:eligible_idx_]
                if len(eligible_artifacts_) == 0:
                    msg = (
                        f"Version {version!s} predates the earliest version "
                        f"{artifacts_matching_name[0].created_at!s}."
                    )
                    raise VersionNotFoundError(msg) from None

                for art in eligible_artifacts_[::-1]:
                    if art.expiry is None or version < art.expiry:
                        artifact = art
                        break
                else:
                    msg = (
                        f"The only available artifacts with name '{name}' as of "
                        f"{version!s} are expired."
                    )
                    raise VersionNotFoundError(msg) from None
                LOG.info(
                    f"Found version {artifact.version} (created {artifact.created_at!s})"
                )
            case ("exact", int()):
                try:
                    # Integer version is 0-indexed
                    artifact = next(
                        art for art in artifacts_matching_name if art.version == version
                    )
                except StopIteration:
                    raise VersionNotFoundError(
                        f"No artifact named {name} with version {version}"
                    ) from None
            case _:
                raise ValueError(
                    "Please provide ``exact`` or ``asof`` for match. ``asof`` is only "
                    "valid for str/datetime versions."
                )

        return artifact

    def __contains__(self, item: str) -> bool:
        """Check if the repository contains an artifact with the given slug or short slug."""
        return any(art.name == item for art in self.artifacts)

    def __getitem__(self, arg: str) -> Artifact:
        """Use brackets to retrieve an artifact by slug.

        Parameters
        ----------
        arg : str
            The slug or short slug for the artifact.

            .. note::

                If you have multiple artifacts with the same short slug, this notation
                will retrieve the first one added to the repository.

        Raises
        ------
        KeyError
            Raised if the slug does not exist.
        """
        for art in self.artifacts:
            if art.name == arg:
                out = art
                break
        else:
            raise KeyError(f"No artifact with name {arg}")

        return out

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate through each artifact and return the dictionary."""
        yield from serialize_artifacts(self.artifacts)
