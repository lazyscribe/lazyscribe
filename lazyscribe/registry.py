"""Create a project registry."""

from __future__ import annotations

from attrs import Factory, define

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

    # def __contains__(self, key: str | "lazyscribe.project.Project") -> bool:
    #     """Check if a project is in the registry."""
    #     match key:
    #         case Project():
    #             return key in self.projects
