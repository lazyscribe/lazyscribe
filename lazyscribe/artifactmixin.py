"""Artifact functionality mixin."""

from datetime import datetime
import inspect
import json
import logging
from typing import Any
import warnings
from lazyscribe.artifacts import Artifact, _get_handler
from attrs import Factory, asdict, define, field, fields, filters, frozen

LOG = logging.getLogger(__name__)


@define
class ArtifactMixin:
    artifacts: list[Artifact] = Factory(factory=lambda: [])

    def log_artifact(
        self,
        name: str,
        value: Any,
        handler: str,
        fname: str | None = None,
        overwrite: bool = False,
        **kwargs,
    ):
        """Log an artifact to the experiment.

        This method associates an artifact with the experiment, but the artifact will
        not be written until :py:meth:`lazyscribe.Project.save` is called.

        Parameters
        ----------
        name : str
            The name of the artifact.
        value : Any
            The object to persist to the filesystem.
        handler : str
            The name of the handler to use for the object.
        fname : str, optional (default None)
            The filename for the artifact. If not provided, it will be derived from the
            name of the artifact and the builtin suffix for each handler.
        overwrite : bool, optional (default False)
            Whether or not to overwrite an existing artifact with the same name. If set to ``True``,
            the previous artifact will be removed and overwritten with the current artifact.
        **kwargs : dict
            Keyword arguments for the write function of the handler.

        Raises
        ------
        RuntimeError
            Raised if an artifact is supplied with the same name as an existing artifact and
            ``overwrite`` is set to ``False``.
        """
        # Retrieve and construct the handler
        self.last_updated = datetime.now()
        handler_cls = _get_handler(handler)
        artifact_handler = handler_cls.construct(
            name=name,
            value=value,
            fname=fname,
            created_at=self.last_updated,
            writer_kwargs=kwargs,
        )
        for index, artifact in enumerate(self.artifacts):
            if artifact.name == name:
                if overwrite:
                    self.artifacts[index] = artifact_handler
                    if handler_cls.output_only:
                        warnings.warn(
                            f"Artifact '{name}' is added. It is not meant to be read back as Python Object",
                            UserWarning,
                            stacklevel=2,
                        )
                    break
                else:
                    raise RuntimeError(
                        f"An artifact with name {name} already exists in the experiment. Please "
                        "use another name or set ``overwrite=True`` to replace the artifact."
                    )
        else:
            self.artifacts.append(artifact_handler)
            if handler_cls.output_only:
                warnings.warn(
                    f"Artifact '{name}' is added. It is not meant to be read back as Python Object",
                    UserWarning,
                    stacklevel=2,
                )

    def load_artifact(self, name: str, validate: bool = True, **kwargs) -> Any:
        """Load a single artifact.

        Parameters
        ----------
        name : str
            The name of the artifact to load.
        validate : bool, optional (default True)
            Whether or not to validate the runtime environment against the artifact
            metadata.
        **kwargs : dict
            Keyword arguments for the handler read function.

        Returns
        -------
        object
            The artifact.
        """
        for artifact in self.artifacts:
            if artifact.name == name:
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
                with self.fs.open(self.dir / self.path / artifact.fname, mode) as buf:
                    out = curr_handler.read(buf, **kwargs)
                if artifact.output_only:
                    warnings.warn(
                        f"Artifact '{name}' is not the original Python Object",
                        UserWarning,
                        stacklevel=2,
                    )
                break
        else:
            raise ValueError(f"No artifact with name {name}")

        return out
