"""Project storing and logging."""

from contextlib import contextmanager
from dataclasses import asdict
from typing import Optional, Union

from .experiment import Experiment, ReadOnlyExperiment


class Project:
    """Project class.

    Parameters
    ----------
    fpath : str
        The location of the project file. If no project file exists, this will be the location
        of the output JSON file when ``save`` is called.
    mode : {"r", "a", "w", "w+"}, optional (default "w")
        The mode for opening the project.

        * ``r``: All existing experiments will be loaded as
          :py:class:`lazyscribe.experiment.ReadOnlyExperiment` and no new experiments can be logged.
        * ``a``: All existing experiments will be loaded as
          :py:class:`lazyscribe.experiment.ReadOnlyExperiment` and new experiments can be added.
        * ``w``: No existing experiments will be loaded.
        * ``w+``: All experiments will be loaded in editable mode as
          :py:class:`lazyscribe.experiment.Experiment`.
    """

    def __init__(self, fpath: Optional[str] = None, mode: str = "w"):
        """Init method."""
        self.fpath = fpath
        self.mode = mode
        self.experiments = []

    def load(self):
        """Load existing experiments."""

    def save(self):
        """Save the project data."""
        _ = [asdict(exp) for exp in self.experiments]

    def get(self, slug: str) -> Union[Experiment, ReadOnlyExperiment]:
        """Retrieve an experiment through the slug."""

    @contextmanager
    def log(self, name: str) -> Experiment:
        """Log an experiment to the project.

        Parameters
        ----------
        name : str
            The name of the experiment.
        
        Yields
        ------
        Experiment
            A new ``Experiment`` data class.

        Raises
        ------
        RuntimeError
            Raised when trying to log a new experiment when the project is in
            read-only mode.
        """
        if self.mode == "r":
            raise RuntimeError("No logging available in read-only mode.")
        experiment = Experiment(name=name)

        try:
            yield experiment

            self.experiments.append(experiment)
        except Exception as exc:
            raise exc

    def __getitem__(self, arg: str) -> Union[Experiment, ReadOnlyExperiment]:
        """Use brackets to retrieve an experiment by slug.

        Raises
        ------
        KeyError
            Raised if the slug does not exist.
        """
