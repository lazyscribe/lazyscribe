"""Test the registry class functionality."""

import pytest

from lazyscribe import Project
from lazyscribe.registry import Registry


def test_registry_indexing(tmp_path):
    """Test creating a project and adding it to the registry."""
    location = tmp_path / "my-project"
    location.mkdir()

    my_registry_ = Registry()
    project = Project(location / "project.json", mode="w")

    # Add the project
    my_registry_.add_project("my-project", project)

    assert my_registry_.projects == {"my-project": project}
    assert my_registry_.search(project.fpath) == "my-project"
    assert "my-project" in my_registry_

    with pytest.raises(KeyError):
        my_registry_["project-is-not-there"]
