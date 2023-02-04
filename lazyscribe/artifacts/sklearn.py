"""Joblib-based handler for scikit-learn objects."""

from attrs import define

from .base import Artifact


@define
class SklearnArtifact(Artifact):
    """Joblib-based handler for scikit-learn objects.

    This handler will store the ``joblib`` and ``scikit-learn`` versions as attributes
    to ensure compatibility between the runtime environment and the artifacts.

    Parameters
    ----------
    sklearn_version : str
        The version of ``scikit-learn`` installed.
    joblib_version : str
        The version of ``joblib`` installed.
    """

    sklearn_version: str
    joblib_version: str

    @classmethod
    def construct(cls):
        """Construct the class with the version information."""
        try:
            import joblib
            import sklearn
        except ImportError:
            raise RuntimeError(
                "Please install ``scikit-learn`` and ``joblib`` to use this handler."
            )

        return cls(
            sklearn_version=sklearn.__version__, joblib_version=joblib.__version__
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
