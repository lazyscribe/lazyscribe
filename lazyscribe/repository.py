"""Repository storing and logging."""

from __future__ import annotations

import inspect
import json
import logging
import warnings
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import fsspec
from attrs import asdict, fields, filters

from lazyscribe._utils import serialize_artifacts, utcnow
from lazyscribe.artifacts import _get_handler
from lazyscribe.artifacts.base import Artifact

LOG = logging.getLogger(__name__)


class Repository:
    """Repository class for holding versioned artifacts.

    Parameters
    ----------
    fpath : str | Path, optional (default "repository.json")
        The location of the repository file. If no repository file exists, this will be the location
        of the output JSON file when ``save`` is called.
    mode : {"r", "a", "w", "w+"}, optional (default "w")
        The mode for opening the repository.

        * ``r``: Repository loaded as read-only: no new artifacts can be logged.
        * ``a``: All existing artifacts will be loaded as
          read-only and new artifacts can be added.
        * ``w``: No existing artifacts will be loaded.
        * ``w+``: All artifacts will be loaded in editable mode.

    Attributes
    ----------
    artifacts : list[Artifact]
        The list of artifacts in the repository.
    """

    def __init__(
        self,
        fpath: str | Path = "repository.json",
        mode: Literal["r", "a", "w", "w+"] = "w",
        **storage_options,
    ):
        """Init method."""
        if isinstance(fpath, str):
            parsed = urlparse(fpath)
            self.fpath = Path(parsed.netloc + parsed.path)
            self.protocol = parsed.scheme or "file"
        else:
            self.fpath = fpath
            self.protocol = "file"
        self.dir = self.fpath.parent
        self.storage_options = storage_options

        # If in ``r``, ``a``, or ``w+`` mode, read in the existing repository.
        self.artifacts: list[Artifact] = []
        self.fs = fsspec.filesystem(self.protocol, **storage_options)

        if mode not in ("r", "a", "w", "w+"):
            raise ValueError("Please provide a valid ``mode`` value.")
        self.mode = mode
        if mode in ("r", "a", "w+") and self.fs.isfile(self.fpath):
            self.load()

    def load(self):
        """Load existing artifacts."""
        with self.fs.open(self.fpath, "r") as infile:
            data = json.load(infile)

        artifacts = []
        for artifact in data:
            handler_cls = _get_handler(artifact.pop("handler"))
            created_at = datetime.fromisoformat(artifact.pop("created_at"))
            artifacts.append(handler_cls.construct(**artifact, created_at=created_at))
        self.artifacts = artifacts

    def log_artifact(
        self,
        name: str,
        value: Any,
        handler: str,
        fname: str | None = None,
        **kwargs,
    ):
        """Log an artifact to the repository.

        This method associates an artifact with the repository, but the artifact will
        not be written until :py:meth:`lazyscribe.Repository.save` is called.

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
        overwrite : bool, optional (default False)
            Whether or not to overwrite an existing artifact with the same name. If set to ``True``,
            the previous artifact will be removed and overwritten with the current artifact.
            If set to ``False``, artifact will be logged with its version incremented.
        **kwargs : dict
            Keyword arguments for the write function of the handler.

        Raises
        ------
        RuntimeError
            Raised if an artifact is supplied with the same name as an existing artifact and
            ``overwrite`` is set to ``False``.
            Also raised if the repository is in read-only mode.
        """
        if self.mode == "r":
            raise RuntimeError("Repository is in read-only mode.")
        # Retrieve and construct the handler
        self.last_updated = utcnow()
        artifacts_matching_name = [art for art in self.artifacts if art.name == name]
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
        **kwargs,
    ) -> Any:
        """Load a single artifact.

        Parameters
        ----------
        name : str
            The name of the artifact to load.
        validate : bool, optional (default True)
            Whether or not to validate the runtime environment against the artifact
            metadata.
        version: datetime.datetime | str | int, optional (default None)
            The version of the artifact to load.
            Can be provided as a datetime corresponding to the ``created_at`` field,
            a string corresponding to the ``created_at`` field in the format ``"%Y-%m-%dT%H:%M:%S"``
            (e.g. ``"2025-01-25T12:36:22"``), or an integer version.
            If set to ``None`` or not provided, defaults to the most recent version.
        **kwargs : dict
            Keyword arguments for the handler read function.

        Returns
        -------
        Any
            The artifact object.
        """
        artifacts_matching_name = [art for art in self.artifacts if art.name == name]
        version = (
            datetime.strptime(version, "%Y-%m-%dT%H:%M:%S")
            if isinstance(version, str)
            else version
        )
        if not artifacts_matching_name:
            raise ValueError(f"No artifact with name {name}") from None
        if version is None:
            artifact = sorted(
                artifacts_matching_name, key=lambda x: x.created_at, reverse=True
            )[0]
        elif isinstance(version, datetime):
            try:
                artifact = next(
                    art for art in artifacts_matching_name if art.created_at == version
                )
            except StopIteration:
                raise ValueError(
                    f"No artifact named {name} with version {version}"
                ) from None
        else:
            try:
                artifact = sorted(artifacts_matching_name, key=lambda x: x.created_at)[
                    version
                ]
            except IndexError:
                raise ValueError(
                    f"No artifact named {name} with version {version}"
                ) from None
        # Construct the handler with relevant parameters.
        artifact_attrs = {
            x: y
            for x, y in inspect.getmembers(artifact)
            if not x.startswith("_") and not inspect.ismethod(y)
        }
        exclude_params = ["value", "fname", "created_at"]
        construct_params = [
            param
            for param in inspect.signature(artifact.construct).parameters
            if param not in exclude_params
        ]
        artifact_attrs = {
            key: value
            for key, value in artifact_attrs.items()
            if key in construct_params
        }

        curr_handler = type(artifact).construct(**artifact_attrs)

        # Validate the handler
        if validate and curr_handler != artifact:
            field_filters = filters.exclude(
                fields(type(artifact)).name,
                fields(type(artifact)).fname,
                fields(type(artifact)).value,
                fields(type(artifact)).created_at,
            )
            raise RuntimeError(
                "Runtime environments do not match. Artifact parameters:\n\n"
                f"{json.dumps(asdict(artifact, filter=field_filters))}"
                "\n\nCurrent parameters:\n\n"
                f"{json.dumps(asdict(curr_handler, filter=field_filters))}"
            )
        # Read in the artifact
        mode = "rb" if curr_handler.binary else "r"
        with self.fs.open(self.dir / artifact.name / artifact.fname, mode) as buf:
            out = curr_handler.read(buf, **kwargs)
        if artifact.output_only:
            warnings.warn(
                f"Artifact '{name}' is not the original Python Object",
                UserWarning,
                stacklevel=2,
            )

        return out

    def save(self):
        """Save the repository data.

        This includes saving any artifact data.
        """
        if self.mode == "r":
            raise RuntimeError("Repository is in read-only mode.")

        data = list(self)
        with self.fs.open(self.fpath, "w") as outfile:
            json.dump(data, outfile, sort_keys=True, indent=4)

        for artifact in self.artifacts:
            # Write the artifact data
            fmode = "wb" if artifact.binary else "w"
            artifact_dir = self.dir / artifact.name
            fpath = artifact_dir / artifact.fname
            if self.fs.isfile(fpath) and artifact.created_at <= datetime.fromtimestamp(
                self.fs.info(fpath)["created"]
            ):
                LOG.debug(
                    f"Artifact {artifact.name} v{artifact.version} already exists and has not been updated"
                )
                continue

            self.fs.makedirs(artifact_dir, exist_ok=True)
            LOG.debug(f"Saving '{artifact.name}' to {fpath!s}...")
            with self.fs.open(fpath, fmode) as buf:
                artifact.write(artifact.value, buf, **artifact.writer_kwargs)
                if artifact.output_only:
                    warnings.warn(
                        f"Artifact '{artifact.name}' is added. It is not meant to be read back as Python Object",
                        UserWarning,
                        stacklevel=2,
                    )

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
