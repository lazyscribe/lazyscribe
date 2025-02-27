"""Test promoting artifacts.

These tests are in a separate module because it requires the interaction between
projects and repositories.
"""

import json
import sys
import zoneinfo
from datetime import datetime

import time_machine

from lazyscribe.project import Project
from lazyscribe.repository import Repository


def test_promote_artifact_dirty(tmp_path):
    """Test promoting an artifact that hasn't been persisted to disk yet."""
    location = tmp_path / "my-project"
    project_location = location / "project.json"
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
    project = Project(project_location)

    with project.log(name="My experiment") as exp:
        with time_machine.travel(
            datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")),
            tick=False,
        ):
            exp.log_artifact(name="features", value=[0, 1, 2], handler="json")
        with time_machine.travel(
            datetime(2025, 3, 1, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
        ):
            exp.promote_artifact(repository, "features")

    assert repository.get_artifact_metadata("features") == {
        "name": "features",
        "fname": "features-20250120132330.json",
        "created_at": "2025-01-20T13:23:30",
        "handler": "json",
        "python_version": ".".join(str(i) for i in sys.version_info[:2]),
        "version": 0,
    }
    assert repository.artifacts[0].value == project["my-experiment"].artifacts[0].value


def test_promote_artifact_clean(tmp_path):
    """Test promoting an artifact that exists on disk already."""
    location = tmp_path / "my-project"
    project_location = location / "project.json"
    project = Project(project_location)

    with (
        project.log("My experiment") as exp,
        time_machine.travel(
            datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")),
            tick=False,
        ),
    ):
        exp.log_artifact(name="features", value=[0, 1, 2], handler="json")

    # Save the project
    project.save()

    repository_location = location / "repository.json"
    repository = Repository(repository_location)

    with time_machine.travel(
        datetime(2025, 3, 1, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        reload_project = Project(project_location, mode="r")
        reload_project["my-experiment"].promote_artifact(repository, "features")

    assert (repository.dir / "features" / "features-20250120132330.json").is_file()
    assert repository.get_artifact_metadata("features") == {
        "name": "features",
        "fname": "features-20250120132330.json",
        "created_at": "2025-01-20T13:23:30",
        "handler": "json",
        "python_version": ".".join(str(i) for i in sys.version_info[:2]),
        "version": 0,
    }

    with open(repository_location) as infile:
        repo_data = json.load(infile)

    assert repo_data == [
        {
            "name": "features",
            "fname": "features-20250120132330.json",
            "created_at": "2025-01-20T13:23:30",
            "handler": "json",
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            "version": 0,
        }
    ]


def test_promote_artifact_new_version(tmp_path):
    """Test promoting a new version of an existing artifact."""
    location = tmp_path / "my-project"
    repository_location = location / "repository.json"
    repository = Repository(repository_location)

    # Log version 0 of the artifact
    with time_machine.travel(
        datetime(2025, 1, 1, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        repository.log_artifact("features", [0, 1], handler="json")

    # Save the repository
    repository.save()

    # Create a project and log a new version of the artifact
    project_location = location / "project.json"
    project = Project(project_location)
    with (
        time_machine.travel(
            datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")),
            tick=False,
        ),
    ):
        with project.log("My experiment") as exp:
            exp.log_artifact(name="features", value=[0, 1, 2], handler="json")

        project.save()

    # Reload the project and repository, promote the new object
    reload_project = Project(project_location, mode="r")
    reload_repository = Repository(repository_location, mode="a")

    reload_project["my-experiment"].promote_artifact(reload_repository, "features")

    assert (repository.dir / "features" / "features-20250120132330.json").is_file()
    assert reload_repository.get_artifact_metadata("features") == {
        "name": "features",
        "fname": "features-20250120132330.json",
        "created_at": "2025-01-20T13:23:30",
        "handler": "json",
        "python_version": ".".join(str(i) for i in sys.version_info[:2]),
        "version": 1,
    }

    with open(repository_location) as infile:
        repo_data = json.load(infile)

    assert repo_data == [
        {
            "name": "features",
            "fname": "features-20250101000000.json",
            "created_at": "2025-01-01T00:00:00",
            "handler": "json",
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            "version": 0,
        },
        {
            "name": "features",
            "fname": "features-20250120132330.json",
            "created_at": "2025-01-20T13:23:30",
            "handler": "json",
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            "version": 1,
        },
    ]
