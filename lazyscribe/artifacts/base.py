"""Base class for new artifact handlers."""

from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

from attrs import define, field


@define
class Artifact(metaclass=ABCMeta):
    """Generic artifact handler that defines the expected interface.

    Artifact handlers are not meant to be initialized directly.

    Parameters
    ----------
    name : str
        The name of the artifact.
    fname : str
        The filename of the artifact.
    value : Any
        The value for the artifact.
    writer_kwargs : Dict
        User provided keyword arguments for writing an artifact. Provided when
        the artifact is logged to an experiment.

    Attributes
    ----------
    alias : str
        The alias for the artifact handler. This value will be supplied to
        :py:meth:`lazyscribe.Experiment.log_artifact`.
    suffix : str
        The standard suffix for the files written and read by this handler.
    binary : bool
        Whether or not the file format for the handler is binary in nature. This
        affects whether or not the file handler uses ``w`` or ``wb``.
    name : str
        The name of the artifact.
    fname : str
        The filename for the artifact.
    value : object
        The value for the artifact.
    """

    alias: ClassVar[str]
    suffix: ClassVar[str]
    binary: ClassVar[bool]
    name: str = field(eq=False)
    fname: str = field(eq=False)
    value: Any = field(eq=False)
    writer_kwargs: Dict = field(eq=False)
    created_at: datetime = field(eq=False)

    @classmethod
    @abstractmethod
    def construct(
        cls,
        name: str,
        value: Optional[Any] = None,
        fname: Optional[str] = None,
        created_at: Optional[datetime] = None,
        writer_kwargs: Optional[Dict] = None,
        **kwargs
    ):
        """Construct the artifact handler.

        This method should use environment variables to capture information that
        is relevant to compatibility between runtime environments.

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
        writer_kwargs : Dict, optional (default None)
            Keyword arguments for writing an artifact to the filesystem. Provided when an artifact
            is logged to an experiment.
        **kwargs : Dict
            Other keyword arguments.
            Usually class attributes obtained from a project JSON.
        """
        pass

    @classmethod
    @abstractmethod
    def read(cls, buf, **kwargs):
        """Read in the artifact.

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

    @classmethod
    @abstractmethod
    def write(cls, obj, buf, **kwargs):
        """Write the artifact to the filesystem.

        Parameters
        ----------
        obj : object
            The object to write to the buffer.
        buf : file-like object
            The buffer from a ``fsspec`` filesystem.
        **kwargs : dict
            Keyword arguments for the write method.
        """
