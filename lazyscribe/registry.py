"""Project registry.

This module defines a class used to make inter-filesystem work
easier.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from attrs import Factory, define

if TYPE_CHECKING:
    from lazyscribe import Project


@define
class Registry:
    """A registry of existing projects to reference by name.

    Parameters
    ----------
    projects : dict[str, lazyscribe.project.Project]
        A dictionary with a key for each available project.
    """

    projects: dict[str, "Project"] = Factory(factory=lambda: {})

    def add_project(self, name: str, project: "Project") -> None:
        """Add a project to the registry.

        Parameters
        ----------
        name : str
            The key for the project.
        project : lazyscribe.project.Project
            The project object itself.
        """
        self.projects[name] = project

    def search(self, fpath: Path) -> str:
        """Find a project from the JSON path.

        This method helps identify a project key in the repository based
        on the location of the JSON file.

        Parameters
        ----------
        fpath : Path
            Path to the project JSON.

        Returns
        -------
        Project
            The project.
        """
        out: str | None = None
        for name, project in self.projects.items():
            if project.fpath == fpath:
                out = name
                break

        return out

    def __getitem__(self, arg: str) -> "Project":
        """Retrieve a project.

        Parameters
        ----------
        arg : str
            The name of a project.

        Returns
        -------
        Project
            The project object.
        """
        try:
            return self.projects[arg]
        except KeyError:
            msg = f"No project with the name '{arg}' in the registry"
            raise ValueError(msg) from KeyError

    def __contains__(self, key: str) -> bool:
        """Check if a project is in the registry.

        Parameters
        ----------
        key : str
            The name of the project.
        """
        return key in self.projects


registry = Registry()
