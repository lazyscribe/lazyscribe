"""Repository release tests."""

import zoneinfo
from datetime import datetime

import pytest
import time_machine

from lazyscribe import Repository
from lazyscribe.release import Release, create_release, find_release


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
        assert release.to_dict() == {
            "tag": "v0.1.0",
            "created_at": "2025-06-01T00:00:00",
            "artifacts": [("my-data", 1), ("my-features", 0)],
        }


def test_load_release():
    """Test creating a release from a dictionary."""
    release = Release(
        tag="v0.1.0", artifacts=[], created_at=datetime(2025, 1, 1, 0, 0, 0)
    )
    new_ = Release.from_dict(
        {"tag": "v0.1.0", "artifacts": [], "created_at": "2025-01-01T00:00:00"}
    )

    assert new_ == release


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


def test_find_release_latest():
    """Test retrieving the latest release."""
    releases = [
        Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
        Release("v0.2.0", [], datetime(2025, 2, 1, 0, 0, 0)),
        Release("v0.2.1", [], datetime(2025, 3, 1, 0, 0, 0)),
    ]
    out = find_release(releases)

    assert out == releases[-1]


def test_find_release_exact_tag():
    """Test finding a release using the tag."""
    releases = [
        Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
        Release("v0.2.0", [], datetime(2025, 2, 1, 0, 0, 0)),
        Release("v0.2.1", [], datetime(2025, 3, 1, 0, 0, 0)),
    ]
    out = find_release(releases, "v0.2.0")

    assert out == releases[1]

    with pytest.raises(ValueError) as excinfo:
        find_release(releases, "v1.0.0")

    assert str(excinfo.value) == "Cannot find release with tag 'v1.0.0'"


def test_find_release_exact_date():
    """Test finding a release with an exact creation date."""
    releases = [
        Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
        Release("v0.2.0", [], datetime(2025, 2, 1, 0, 0, 0)),
        Release("v0.2.1", [], datetime(2025, 3, 1, 0, 0, 0)),
    ]
    out = find_release(releases, datetime(2025, 1, 1, 0, 0, 0))

    assert out == releases[0]

    with pytest.raises(ValueError) as excinfo:
        find_release(releases, datetime(2025, 6, 1, 0, 0, 0))

    assert (
        str(excinfo.value)
        == "Cannot find release with creation date of 2025-06-01 00:00:00"
    )


def test_find_release_raise_error_asof_str():
    """Test raising an error when we try to use an asof search with a string."""
    with pytest.raises(ValueError) as excinfo:
        find_release([], "v0.1.0", match="asof")

    assert str(excinfo.value) == (
        "Cannot perform an ``asof`` match using a tag. Please provide a ``datetime.datetime`` value "
        "to perform an ``asof`` match."
    )


def test_find_release_asof_date():
    """Test finding a release using an asof search."""
    releases = [
        Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
        Release("v0.2.0", [], datetime(2025, 2, 1, 0, 0, 0)),
        Release("v0.2.1", [], datetime(2025, 3, 1, 0, 0, 0)),
    ]

    # First, try retrieving a release that predates the earliest
    with pytest.raises(ValueError) as excinfo:
        find_release(releases, datetime(2024, 12, 15, 0, 0, 0), match="asof")

    assert str(excinfo.value) == (
        "Creation date 2024-12-15 00:00:00 predates the earliest release: "
        "'v0.1.0' (2025-01-01 00:00:00)"
    )

    # Next, perform a successful asof search
    out = find_release(releases, datetime(2025, 2, 15, 0, 0, 0), match="asof")
    assert out == releases[1]

    # Retrieve the latest when we go beyond the last creation date
    out = find_release(releases, datetime(2025, 6, 1, 0, 0, 0), match="asof")
    assert out == releases[-1]


def test_find_release_invalid_match():
    """Test raising an error when match is invalid."""
    with pytest.raises(ValueError) as excinfo:
        find_release([], "v0.1.0", match="match-this-idiot")

    assert (
        str(excinfo.value)
        == "Invalid parameterization. Please provide ``exact`` or ``asof`` for ``match``."
    )
