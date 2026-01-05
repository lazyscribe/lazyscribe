"""Test promoting artifacts.

These tests are in a separate module because it requires the interaction between
projects and repositories.
"""

import json
import zoneinfo
from datetime import datetime

import pytest
import time_machine
from fsspec.implementations.local import LocalFileSystem
from fsspec.registry import register_implementation

from lazyscribe.exception import ArtifactLoadError, ArtifactLogError, SaveError
from lazyscribe.project import Project
from lazyscribe.repository import Repository


def test_promote_artifact_nonexistent():
    """Test raising an error when a user promotes a non-existent artifact."""
    project = Project()
    repository = Repository()

    with pytest.raises(ArtifactLoadError), project.log("My experiment") as exp:
        exp.promote_artifact(repository, "fake-artifact")


def test_promoting_old_artifact(tmp_path):
    """Test raising an error when promoting an artifact that is older than the most recent version."""
    location = tmp_path / "my-project"
    repository_location = location / "repository.json"
    repository = Repository(repository_location)

    # Log version 0 of the artifact
    with time_machine.travel(
        datetime(2025, 1, 1, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        repository.log_artifact("features", [0, 1], handler="json")

    repository.save()

    # Create an old project and promote
    project_location = location / "project.json"
    project = Project(project_location)
    with (
        time_machine.travel(
            datetime(2024, 12, 31, tzinfo=zoneinfo.ZoneInfo("UTC")),
            tick=False,
        ),
    ):
        with project.log("My experiment") as exp:
            exp.log_artifact(name="features", value=[0, 1, 2], handler="json")

        project.save()

    reload_project = Project(project_location, mode="r")
    reload_repository = Repository(repository_location, mode="w+")

    with pytest.raises(ArtifactLogError):
        reload_project["my-experiment"].promote_artifact(reload_repository, "features")


@time_machine.travel(datetime(2025, 1, 1, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False)
def test_promote_equal_artifact(tmp_path):
    """Test promoting an artifact that has the exact same creation date."""
    location = tmp_path / "my-project"
    repository_location = location / "repository.json"
    repository = Repository(repository_location)

    # Log version 0 of the artifact
    repository.log_artifact("features", [0, 1], handler="json")

    repository.save()

    # Create an old project and promote
    project_location = location / "project.json"
    project = Project(project_location)
    with project.log("My experiment") as exp:
        exp.log_artifact(name="features", value=[0, 1, 2], handler="json")

    project.save()

    reload_project = Project(project_location, mode="r")
    reload_repository = Repository(repository_location, mode="w+")

    with pytest.raises(ArtifactLogError):
        reload_project["my-experiment"].promote_artifact(reload_repository, "features")


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
        "expiry": None,
        "handler": "json",
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
        "expiry": None,
        "handler": "json",
        "version": 0,
    }

    with open(repository_location) as infile:
        repo_data = json.load(infile)

    assert repo_data == [
        {
            "name": "features",
            "fname": "features-20250120132330.json",
            "created_at": "2025-01-20T13:23:30",
            "expiry": None,
            "handler": "json",
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
    reload_repository = Repository(repository_location, mode="w+")

    reload_project["my-experiment"].promote_artifact(reload_repository, "features")

    assert (repository.dir / "features" / "features-20250120132330.json").is_file()
    assert reload_repository.get_artifact_metadata("features") == {
        "name": "features",
        "fname": "features-20250120132330.json",
        "created_at": "2025-01-20T13:23:30",
        "expiry": None,
        "handler": "json",
        "version": 1,
    }

    with open(repository_location) as infile:
        repo_data = json.load(infile)

    assert repo_data == [
        {
            "name": "features",
            "fname": "features-20250101000000.json",
            "created_at": "2025-01-01T00:00:00",
            "expiry": None,
            "handler": "json",
            "version": 0,
        },
        {
            "name": "features",
            "fname": "features-20250120132330.json",
            "created_at": "2025-01-20T13:23:30",
            "expiry": None,
            "handler": "json",
            "version": 1,
        },
    ]


def test_mismatched_protocol(tmp_path):
    """Test promoting an artifact with mismatched fsspec protocols."""
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
    # Modify the repository spec to have a mismatched protocol
    repository = Repository(
        "github://" + str(repository_location),
        org="lazyscribe",
        repo="lazyscribe",
        mode="w",
    )

    reload_project = Project(project_location, mode="r")
    with pytest.raises(ArtifactLogError):
        reload_project["my-experiment"].promote_artifact(repository, "features")


def test_raised_save_error(tmp_path):
    """Test promoting an artifact and having it fail on save, reverting the change."""
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

    # Create a fake protocol that errors on open
    class FakeProtocol(LocalFileSystem):
        """Fake filesystem protocol."""

        protocol = "fake"

        def open(
            self,
            path,
            mode="rb",
            block_size=None,
            cache_options=None,
            compression=None,
            **kwargs,
        ):
            """Return a file-like object."""
            if mode == "w":
                raise ValueError("Error!")
            else:
                return super().open(
                    path, mode, block_size, cache_options, compression, **kwargs
                )

    # Register the fake implementation
    register_implementation("fake", FakeProtocol)

    # Open the project and repository using the fake protocol
    repository_location = location / "repository.json"
    repository = Repository("fake://" + str(repository_location))

    with time_machine.travel(
        datetime(2025, 3, 1, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        reload_project = Project("fake://" + str(project_location), mode="r")
        with pytest.raises(SaveError):
            reload_project["my-experiment"].promote_artifact(repository, "features")

    # Ensure the artifact has been deleted
    assert not (repository.dir / "features" / "features-20250120132330.json").is_file()
    assert len(repository.artifacts) == 0
