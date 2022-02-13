"""Project storing and logging."""

from __future__ import annotations

from contextlib import contextmanager
import getpass
import json
from pathlib import Path
from typing import List, Optional, Union

from .experiment import Experiment, ReadOnlyExperiment


class Project:
    """Project class.

    Parameters
    ----------
    fpath : str, optional (default "project.json")
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
    author : str, optional (default None)
        The project author. This author will be used for any new experiments or modifications to
        existing experiments. If not supplied, ``getpass.getuser()`` will be used.
    """

    def __init__(
        self,
        fpath: str = "project.json",
        mode: str = "w",
        author: Optional[str] = None
    ):
        """Init method."""
        if isinstance(fpath, str):
            self.fpath = Path(fpath)
        else:
            self.fpath = fpath

        # If in ``r``, ``a``, or ``w+`` mode, read in the existing project.
        self.experiments: List[Union[Experiment, ReadOnlyExperiment]] = []
        self.mode = mode
        if mode in ("r", "a", "w+"):
            self.load()

        self.author = getpass.getuser() if author is None else author

    def load(self):
        """Load existing experiments."""
        # Read in the project JSON
        # If in ``r`` or ``a`` mode, instantiate existing experiments as read-only
        # Otherwise, make them editable
        # Dependencies need to be read as experiments

    def save(self):
        """Save the project data."""
        if self.mode == "r":
            raise RuntimeError("Project is in read-only mode.")
        data = [exp.to_dict() for exp in self.experiments]
        with open(self.fpath, "w") as outfile:
            json.dump(data, outfile)

    def merge(self, other: Project) -> Project:
        """Merge two projects."""

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
        experiment = Experiment(name=name, project=self.fpath, author=self.author)

        try:
            yield experiment

            self.experiments.append(experiment)
        except Exception as exc:
            raise exc

    def __getitem__(self, arg: str) -> Union[Experiment, ReadOnlyExperiment]:
        """Use brackets to retrieve an experiment by slug.

        Parameters
        ----------
        arg : str
            The slug or short slug for the experiment.

            .. note::

                If you have multiple experiments with the same short slug, this notation
                will retrieve the first one added to the project.

        Raises
        ------
        KeyError
            Raised if the slug does not exist.
        """
        for exp in self.experiments:
            if exp.slug == arg or exp.short_slug == arg:
                out = exp
                break
        else:
            raise KeyError(f"No experiment with slug {arg}")

        return out
