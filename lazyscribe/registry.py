"""Project registry.

This module defines a class used to make inter-filesystem work
easier.
"""

from __future__ import annotations

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

    projects: dict[str, Project] = Factory(factory=lambda: {})

    def add_project(self, name: str, project: Project) -> None:
        """Add a project to the registry.

        Parameters
        ----------
        name : str
            The key for the project.
        project : lazyscribe.project.Project
            The project object itself.
        """
        self.projects[name] = project

    def search(self, fpath: Path) -> str | None:
        """Find a project from the JSON path.

        This method helps identify a project key in the repository based
        on the location of the JSON file.

        Parameters
        ----------
        fpath : pathlib.Path
            Path to the project JSON.

        Returns
        -------
        str | None
            If it exists, the key reference for the project in the registry.
        """
        out: str | None = None
        for name, project in self.projects.items():
            if project.fpath == fpath:
                out = name
                break

        return out

    def __getitem__(self, arg: str) -> Project:
        """Retrieve a project.

        Parameters
        ----------
        arg : str
            The name of a project.

        Returns
        -------
        lazyscribe.project.Project
            The project object.

        Raises
        ------
        KeyError
            Raised if the project name does not exists in the registry.
        """
        try:
            return self.projects[arg]
        except KeyError as exc:
            msg = f"No project with the name '{arg}' in the registry"
            raise KeyError(msg) from exc

    def __contains__(self, key: str) -> bool:
        """Check if a project is in the registry.

        Parameters
        ----------
        key : str
            The name of the project.

        Returns
        -------
        bool
            Whether the project name exists in the registry.
        """
        return key in self.projects


registry = Registry()
