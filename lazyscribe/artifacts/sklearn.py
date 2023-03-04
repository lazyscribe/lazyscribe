"""Joblib-based handler for scikit-learn objects."""

from typing import Any, ClassVar, Optional

from attrs import define
from slugify import slugify

from .base import Artifact


@define(auto_attribs=True)
class SklearnArtifact(Artifact):
    """Joblib-based handler for scikit-learn objects.

    This handler will store the ``joblib`` and ``scikit-learn`` versions as attributes
    to ensure compatibility between the runtime environment and the artifacts.

    .. important::

        This class is not meant to be initialized directly. Please use the ``construct``
        method.

    Parameters
    ----------
    sklearn_version : str
        The version of ``scikit-learn`` installed.
    joblib_version : str
        The version of ``joblib`` installed.
    """

    alias: ClassVar[str] = "scikit-learn"
    suffix: ClassVar[str] = "joblib"
    binary: ClassVar[bool] = True
    sklearn_version: str
    joblib_version: str

    @classmethod
    def construct(
        cls, name: str, value: Optional[Any] = None, fname: Optional[str] = None, **kwargs
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
        **kwargs : Dict
            Keyword arguments for writing an artifact to the filesystem. Provided when an artifact
            is logged to an experiment
        """
        try:
            import joblib
            import sklearn
        except ImportError:
            raise RuntimeError(
                "Please install ``scikit-learn`` and ``joblib`` to use this handler."
            )

        return cls(
            name=name,
            value=value,
            fname=fname or f"{slugify(name)}.{cls.suffix}",
            writer_kwargs=kwargs,
            sklearn_version=sklearn.__version__,
            joblib_version=joblib.__version__,
        )

    @classmethod
    def read(cls, buf, **kwargs):
        """Read the ``scikit-learn`` object.

        Parameters
        ----------
        buf : file-like object
            The buffer from the ``fsspec`` filesystem.
        **kwargs : dict
            Keyword arguments for ``joblib.load``.

        Returns
        -------
        Any
            The ``scikit-learn`` object.
        """
        from joblib import load

        return load(buf, **kwargs)

    @classmethod
    def write(cls, obj, buf, **kwargs):
        """Write the ``scikit-learn`` object to the filesystem.

        Parameters
        ----------
        obj : object
            The ``scikit-learn`` object to write.
        buf : file-like object
            The buffer from the ``fsspec`` filesystem.
        **kwargs : dict
            Keyword arguments for :py:meth:`joblib.load`.
        """
        from joblib import dump

        dump(obj, buf, **kwargs)
