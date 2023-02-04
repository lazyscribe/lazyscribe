"""Base class for new artifact handlers."""

from abc import ABCMeta, abstractclassmethod


class Artifact(metaclass=ABCMeta):
    """Generic artifact handler that defines the expected interface."""

    @abstractclassmethod
    def construct(cls):
        """Construct the artifact handler.

        This method should use environment variables to capture information that
        is relevant to compatibility between runtime environments.
        """
        pass

    @abstractclassmethod
    def read(cls, buf, **kwargs):
        """Method for reading in the artifact.

        Parameters
        ----------
        buf : file-like object
            The buffer from a ``fsspec`` filesystem.
        **kwargs : dict
            Keyword arguments for the read method.

        Returns
        -------
        Any
            The artifact.
        """

    @abstractclassmethod
    def write(cls, obj, buf, **kwargs):
        """Method for writing the artifact to the filesystem.

        Parameters
        ----------
        obj : object
            The object to write to the buffer.
        buf : file-like object
            The buffer from a ``fsspec`` filesystem.
        **kwargs : dict
            Keyword arguments for the write method.
        """
