"""Sub-population tests."""

from __future__ import annotations

import pickle
import warnings
from pathlib import Path
from typing import Any

from attrs import Factory, asdict, define, field, fields, filters, frozen
from fsspec.implementations.local import LocalFileSystem
from fsspec.spec import AbstractFileSystem

from lazyscribe._utils import (
    load_artifact_from,
    serializer,
    utcnow,
)
from lazyscribe.artifacts import _get_handler
from lazyscribe.artifacts.base import Artifact
from lazyscribe.exception import ArtifactLogError


@define
class Test:
    """Sub-population tests.

    These objects should only be instantiated within an experiment. A test is associated with
    some subset of the entire experiment. For example, a test could be used to evaluate the
    performance of a model against a specific subpopulation.

    Parameters
    ----------
    name : str
        The name of the test.
    description : str, optional (default None)
        A description of the test.
    metrics : dict[str, float | int], optional (default {})
        A dictionary of metric values. Each metric value can be an individual value or a list.
    parameters : dict[str, Any], optional (default {})
        A dictionary of test parameters. The key must be a string but the value can be anything.
    artifacts : list[lazyscribe.artifacts.base.Artifact], optional (default [])
        List of :py:class:`lazyscribe.artifact.base.Artifact` objects corresponding to test
        artifacts.
    path : pathlib.Path, optional (default pathlib.Path("."))
        The path to the test's artifact directory. Set automatically when the test is created
        via :py:meth:`lazyscribe.experiment.Experiment.log_test`.
    fs : fsspec.spec.AbstractFileSystem, optional (default fsspec.implementations.local.LocalFileSystem())
        The filesystem to use for reading and writing artifacts.
    """

    # Tell pytest it's not a Python test class
    __test__ = False

    name: str = field()
    description: str | None = Factory(lambda: None)
    metrics: dict[str, float | int] = Factory(lambda: {})
    parameters: dict[str, Any] = Factory(lambda: {})
    artifacts: list[Artifact] = Factory(lambda: [])
    path: Path = field(eq=False)
    fs: AbstractFileSystem = field(eq=False)

    @path.default
    def _path_factory(self) -> Path:
        """Default path."""
        return Path(".")

    @fs.default
    def _fs_default(self) -> AbstractFileSystem:
        """Default filesystem."""
        return LocalFileSystem()

    def log_metric(self, name: str, value: float | int) -> None:
        """Log a metric to the test.

        This method will overwrite existing keys.

        Parameters
        ----------
        name : str
            Name of the metric.
        value : int | float
            Value of the metric.
        """
        # Attribute reassignment (not in-place mutation) so @frozen raises FrozenInstanceError on ReadOnlyTest
        self.metrics = self.metrics | {name: value}

    def __str__(self) -> str:
        """Shortened string representation."""
        return f"<lazyscribe.test.Test at {hex(id(self))}>"

    def log_parameter(self, name: str, value: Any) -> None:
        """Log a parameter to the test.

        This method will overwrite existing keys.

        Parameters
        ----------
        name : str
            The name of the parameter.
        value : Any
            The parameter itself.
        """
        # Attribute reassignment (not in-place mutation) so @frozen raises FrozenInstanceError on ReadOnlyTest
        self.parameters = self.parameters | {name: value}

    def log_artifact(
        self,
        name: str,
        value: Any,
        handler: str,
        fname: str | None = None,
        overwrite: bool = False,
        **kwargs: Any,
    ) -> None:
        """Log an artifact to the test.

        This method associates an artifact with the test, but the artifact will
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
            Whether or not to overwrite an existing artifact with the same name.
        **kwargs
            Keyword arguments for the write function of the handler.

        Raises
        ------
        lazyscribe.exception.ArtifactLogError
            Raised if an artifact is supplied with the same name as an existing artifact and
            ``overwrite`` is set to ``False``.
        """
        handler_cls = _get_handler(handler)
        artifact_handler = handler_cls.construct(
            name=name,
            value=value,
            fname=fname,
            created_at=utcnow(),
            writer_kwargs=kwargs,
        )
        for index, artifact in enumerate(self.artifacts):
            if artifact.name == name:
                if overwrite:
                    new_artifacts = list(self.artifacts)
                    new_artifacts[index] = artifact_handler
                    self.artifacts = (
                        new_artifacts  # raises FrozenInstanceError on ReadOnlyTest
                    )
                    if handler_cls.output_only:
                        warnings.warn(
                            f"Artifact '{name}' is added. It is not meant to be read back as Python Object",
                            UserWarning,
                            stacklevel=2,
                        )
                    break
                else:
                    raise ArtifactLogError(
                        f"An artifact with name {name} already exists in the test. Please "
                        "use another name or set ``overwrite=True`` to replace the artifact."
                    )
        else:
            self.artifacts = [
                *self.artifacts,
                artifact_handler,
            ]  # raises FrozenInstanceError on ReadOnlyTest
            if handler_cls.output_only:
                warnings.warn(
                    f"Artifact '{name}' is added. It is not meant to be read back as Python Object",
                    UserWarning,
                    stacklevel=2,
                )

    def load_artifact(self, name: str, validate: bool = True, **kwargs: Any) -> Any:
        """Load a single artifact.

        Parameters
        ----------
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
        return load_artifact_from(
            self.artifacts, self.path, self.fs, name, validate, **kwargs
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the test to a dictionary.

        Returns
        -------
        dict[str, Any]
            The test dictionary.
        """
        return asdict(
            self,
            value_serializer=serializer,
            filter=filters.exclude(fields(Test).path, fields(Test).fs),
        )

    def __getstate__(self) -> dict:
        """Serialize the test.

        This function is useful when we want to serialize higher-level Lazyscribe
        objects for multiprocessing.
        """
        state = asdict(self)
        # Check for artifacts
        artifacts_ = []
        for art in self.artifacts:
            artifacts_.append(pickle.dumps(art))
        state["artifacts"] = artifacts_

        return state

    def __setstate__(self, state: dict) -> None:
        """Deserialize the test.

        All we need to do is assign the attributes, with the notable exception of
        artifact handlers.
        """
        for key, value in state.items():
            match key:
                case "artifacts":
                    self.artifacts = [pickle.loads(art) for art in value]
                case _:
                    setattr(self, key, value)


@frozen
class ReadOnlyTest(Test):
    """Immutable version of the test."""

    def __str__(self) -> str:
        """Shortened string representation."""
        return f"<lazyscribe.test.ReadOnlyTest at {hex(id(self))}>"
