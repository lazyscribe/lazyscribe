"""Joblib-based handler for pickle-serializable objects."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from attrs import define
from importlib_metadata import packages_distributions
from importlib_metadata import version as importlib_version
from slugify import slugify

from lazyscribe._utils import utcnow
from lazyscribe.artifacts.base import Artifact


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

    Parameters
    ----------
    package : str
        The root module name of the python object to be serialized.
    package_version : str
        The installed version of the package pertaining to the python object to be
        serialized.
    joblib_version : str
        The version of ``joblib`` installed.
    """

    alias: ClassVar[str] = "joblib"
    suffix: ClassVar[str] = "joblib"
    binary: ClassVar[bool] = True
    output_only: ClassVar[bool] = False
    package: str
    package_version: str
    joblib_version: str

    @classmethod
    def construct(
        cls,
        name: str,
        value: Any = None,
        fname: str | None = None,
        created_at: datetime | None = None,
        writer_kwargs: dict | None = None,
        version: int = 0,
        package: str | None = None,
        **kwargs,
    ):
        """Construct the class with the version information.

        Parameters
        ----------
        name : str
            The name of the artifact.
        value : object, optional (default None)
            The value for the artifact. The default value of ``None`` is used when
            an experiment is loaded from the project JSON.
        fname : str, optional (default None)
            The filename of the artifact. If not provided, this value will be derived from
            the name of the artifact and the suffix for the class.
        created_at : datetime, optional (default None)
            When the artifact was created. If not supplied, :py:meth:`datetime.now` will be used.
        package: str, optional (default None)
            The package name or root module name of the serializable python object.
            Note: this may be different from the distribution name. e.g ``scikit-learn`` is
            a distribution name, where as ``sklearn`` is the corresponding package name.
        writer_kwargs : dict, optional (default None)
            Keyword arguments for writing an artifact to the filesystem. Provided when an artifact
            is logged to an experiment.
        version : int, optional (default 0)
            Integer version to be used for versioning artifacts.
        **kwargs : dict
            Other keyword arguments.
            Usually class attributes obtained from a project JSON.
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
            raise RuntimeError(
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
            package=package,
            package_version=kwargs.get("package_version")
            or importlib_version(distribution),
            joblib_version=kwargs.get("joblib_version") or joblib.__version__,
        )

    @classmethod
    def read(cls, buf, **kwargs):
        """Read the python object.

        Parameters
        ----------
        buf : file-like object
            The buffer from the ``fsspec`` filesystem.
        **kwargs : dict
            Keyword arguments for ``joblib.load``.

        Returns
        -------
        Any
            The python object.
        """
        from joblib import load

        return load(buf, **kwargs)

    @classmethod
    def write(cls, obj, buf, **kwargs):
        """Write the python object to the filesystem.

        Parameters
        ----------
        obj : object
            The python object to write.
        buf : file-like object
            The buffer from the ``fsspec`` filesystem.
        **kwargs : dict
            Keyword arguments for :py:meth:`joblib.load`.
        """
        from joblib import dump

        dump(obj, buf, **kwargs)
