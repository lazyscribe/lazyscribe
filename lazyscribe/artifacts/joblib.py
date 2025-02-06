"""Joblib-based handler for pickle-serializable objects."""

from __future__ import annotations

from datetime import datetime
from io import IOBase
from typing import Any, ClassVar

from attrs import define, field
from importlib_metadata import packages_distributions
from importlib_metadata import version as importlib_version
from slugify import slugify

from lazyscribe._utils import utcnow
from lazyscribe.artifacts.base import Artifact
from lazyscribe.exception import ArtifactError


@define(auto_attribs=True)
class JoblibArtifact(Artifact):
    """Handler for pickle-serializable objects through ``joblib`` package.

    .. important::

        ``joblib`` package should be installed to use this handler.

    This handler will store the ``joblib`` version and the package (or the root module
    of the ``value``) name and version as attributes to ensure compatibility between
    the runtime environment and the artifacts.

    .. important::

        This class is not meant to be initialized directly. Please use the ``construct``
        method.

    Class Attributes
    ----------------
    See also "Class Attributes" of :py:class:`lazyscribe.artifacts.base.Artifact`.

    alias : str = "json"
    suffix : str = "json"
    binary : bool = False
    output_only : bool = False

    Attributes
    ----------
    :cvar alias : str = "json"
    :cvar suffix : str = "json"
    :cvar binary : bool = False
    :cvar output_only : bool = False

    package : str
        The root module name of the Python object to be serialized.
    package_version : str
        The installed version of the package pertaining to the Python object to be
        serialized.
    joblib_version : str
        The version of ``joblib`` installed.
    """

    alias: ClassVar[str] = "joblib"
    suffix: ClassVar[str] = "joblib"
    binary: ClassVar[bool] = True
    output_only: ClassVar[bool] = False
    package: str = field()
    package_version: str = field()
    joblib_version: str = field()

    @classmethod
    def construct(
        cls,
        name: str,
        value: Any = None,
        fname: str | None = None,
        created_at: datetime | None = None,
        writer_kwargs: dict[str, Any] | None = None,
        version: int = 0,
        dirty: bool = True,
        package: str | None = None,
        **kwargs: Any,
    ) -> JoblibArtifact:
        """Construct the class with the version information.

        Parameters
        ----------
        name : str
            The name of the artifact.
        value : Any, optional (default None)
            The value for the artifact. The default value of ``None`` is used when
            an experiment is loaded from the project JSON.
        fname : str, optional (default None)
            The filename for the artifact. If set to ``None`` or not provided, it will be derived from
            the name of the artifact and the suffix for the class.
        created_at : datetime.datetime, optional (default ``lazyscribe._utils.utcnow()``)
            When the artifact was created (in UTC).
        writer_kwargs : dict[str, Any], optional (default {})
            Keyword arguments for writing an artifact to the filesystem. Provided when an artifact
            is logged to an experiment.
        version : int, optional (default 0)
            Integer version to be used for versioning artifacts.
        dirty : bool, optional (default True)
            Whether or not this artifact should be saved when :py:meth:`lazyscribe.project.Project.save`
            or :py:meth:`lazyscribe.repository.Repository.save` is called. This decision is based
            on whether the artifact is new or has been updated.
        package : str, optional
            The package name or root module name of the serializable Python object.
            Note: this may be different from the distribution name. e.g ``scikit-learn`` is
            a distribution name, where as ``sklearn`` is the corresponding package name.
        package_version : str, optional
            Version of the package corresponding to the serializable Python object.
        joblib_version : str, optional
            Installed version of ``joblib``.

        Returns
        -------
        JoblibArtifact
            The artifact.

        Raises
        ------
        ValueError
            Raised if the class is constructed without arguments for both ``package`` and ``value``.
        AttributeError
            Raised if the root name of the package corresponding to the serializable Python object cannot be identified.
        ArtifactError
            Raised if ``joblib`` is not available.
        """
        if package is None:
            if value is None:
                raise ValueError(
                    "If no ``package`` is specified, you must supply a ``value``."
                )
            try:
                package = value.__module__.split(".")[0]
            except AttributeError as err:
                raise AttributeError(
                    "Unable to identify the package based on the supplied ``value``. "
                    "Please provide an argument for ``package``."
                ) from err

        try:
            distribution = packages_distributions()[package][0]
        except KeyError as err:
            raise ValueError(f"{package} was not found.") from err

        try:
            import joblib
        except ImportError as err:
            raise ArtifactError(
                "Please install ``joblib`` to use this handler."
            ) from err
        created_at = created_at or utcnow()
        return cls(
            name=name,
            value=value,
            fname=fname
            or f"{slugify(name)}-{slugify(created_at.strftime('%Y%m%d%H%M%S'))}.{cls.suffix}",
            created_at=created_at,
            writer_kwargs=writer_kwargs or {},
            version=version,
            dirty=dirty,
            package=package,
            package_version=kwargs.get("package_version")
            or importlib_version(distribution),
            joblib_version=kwargs.get("joblib_version") or joblib.__version__,
        )

    @classmethod
    def read(cls, buf: IOBase, **kwargs: Any) -> Any:
        """Read the Python object.

        Parameters
        ----------
        buf : file-like object
            The buffer from the ``fsspec`` filesystem.
        **kwargs
            Keyword arguments for ``joblib.load``.

        Returns
        -------
        Any
            The Python object.
        """
        from joblib import load

        return load(buf, **kwargs)

    @classmethod
    def write(cls, obj: Any, buf: IOBase, **kwargs: Any) -> None:
        """Write the Python object to the filesystem.

        Parameters
        ----------
        obj : Any
            The Python object to write.
        buf : file-like object
            The buffer from the ``fsspec`` filesystem.
        **kwargs
            Keyword arguments for :py:meth:`joblib.load`.
        """
        from joblib import dump

        dump(obj, buf, **kwargs)
