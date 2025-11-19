"""Repository release tests."""

import zoneinfo
from datetime import datetime

import time_machine

from lazyscribe import Repository
from lazyscribe.release import Release, create_release


def test_repository_release():
    """Test creating a release from a repository."""
    repository = Repository()
    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 1}], handler="json")
        repository.log_artifact("my-features", [0], handler="json")

    with time_machine.travel(
        datetime(2025, 1, 21, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 2}], handler="json")

    # Generate the release
    with time_machine.travel(
        datetime(2025, 6, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        release = create_release(repository, "v0.1.0")

        assert release == Release(
            tag="v0.1.0",
            artifacts=[
                ("my-data", 1),
                ("my-features", 0),
            ],
        )


def test_repository_release_filter():
    """Test creating a repository release and using it to filter the repository."""
    repository = Repository()
    # Log first version of our first two artifacts
    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 1}], handler="json")
        repository.log_artifact("my-features", [0], handler="json")

    with time_machine.travel(
        datetime(2025, 1, 21, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 2}], handler="json")

    # Generate the release
    with time_machine.travel(
        datetime(2025, 6, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        release = create_release(repository, "v0.1.0")

    with time_machine.travel(
        datetime(2025, 1, 22, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-features", [0, 1], handler="json")
        repository.log_artifact("my-metadata", {"process_ver": 1.0}, handler="json")

    # Now, filter the repository based on the release
    new_ = repository.filter(version=release.artifacts)

    assert len(new_.artifacts) == 2
    assert new_["my-data"] == repository._search_artifact_versions("my-data", 1)
    assert new_["my-features"] == repository._search_artifact_versions("my-features", 0)
