"""Repository release tests."""

import json
import logging
import zoneinfo
from datetime import datetime

import pytest
import time_machine

from lazyscribe import Repository
from lazyscribe import release as lzr
from lazyscribe.exception import VersionNotFoundError


def test_repository_release(tmp_path):
    """Test creating a release from a repository."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location, mode="w")
    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 1}], handler="json")
        repository.log_artifact("my-features", [0], handler="json")

    with time_machine.travel(
        datetime(2025, 1, 21, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 2}], handler="json")

    repository.save()
    repository = Repository(repository_location, mode="r")

    # Generate the release
    with time_machine.travel(
        datetime(2025, 6, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        release = lzr.create_release(repository, "v0.1.0")

        assert release == lzr.Release(
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


def test_convert_release():
    """Test creating a release from a dictionary."""
    release = lzr.Release(
        tag="v0.1.0", artifacts=[], created_at=datetime(2025, 1, 1, 0, 0, 0)
    )
    new_ = lzr.Release.from_dict(
        {"tag": "v0.1.0", "artifacts": [], "created_at": "2025-01-01T00:00:00"}
    )

    assert new_ == release


def test_repository_release_filter(tmp_path):
    """Test creating a repository release and using it to filter the repository."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location, mode="w")
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

    repository.save()
    saved_ = Repository(repository_location, mode="r")

    # Generate the release
    with time_machine.travel(
        datetime(2025, 6, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        release = lzr.create_release(saved_, "v0.1.0")

    with time_machine.travel(
        datetime(2025, 1, 22, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-features", [0, 1], handler="json")
        repository.log_artifact("my-metadata", {"process_ver": 1.0}, handler="json")

    repository.save()
    saved_ = Repository(repository_location, mode="r")

    # Now, filter the repository based on the release
    new_ = saved_.filter(version=release.artifacts)

    assert len(new_.artifacts) == 2
    assert new_["my-data"] == repository._search_artifact_versions("my-data", 1)
    assert new_["my-features"] == repository._search_artifact_versions("my-features", 0)


def test_find_release_latest():
    """Test retrieving the latest release."""
    releases = [
        lzr.Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
        lzr.Release("v0.2.0", [], datetime(2025, 2, 1, 0, 0, 0)),
        lzr.Release("v0.2.1", [], datetime(2025, 3, 1, 0, 0, 0)),
    ]
    out = lzr.find_release(releases)

    assert out == releases[-1]


def test_find_release_exact_tag():
    """Test finding a release using the tag."""
    releases = [
        lzr.Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
        lzr.Release("v0.2.0", [], datetime(2025, 2, 1, 0, 0, 0)),
        lzr.Release("v0.2.1", [], datetime(2025, 3, 1, 0, 0, 0)),
    ]
    out = lzr.find_release(releases, "v0.2.0")

    assert out == releases[1]

    with pytest.raises(VersionNotFoundError) as excinfo:
        lzr.find_release(releases, "v1.0.0")

    assert str(excinfo.value) == "Cannot find release with tag 'v1.0.0'"


def test_find_release_exact_date():
    """Test finding a release with an exact creation date."""
    releases = [
        lzr.Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
        lzr.Release("v0.2.0", [], datetime(2025, 2, 1, 0, 0, 0)),
        lzr.Release("v0.2.1", [], datetime(2025, 3, 1, 0, 0, 0)),
    ]
    out = lzr.find_release(releases, datetime(2025, 1, 1, 0, 0, 0))

    assert out == releases[0]

    with pytest.raises(VersionNotFoundError) as excinfo:
        lzr.find_release(releases, datetime(2025, 6, 1, 0, 0, 0))

    assert (
        str(excinfo.value)
        == "Cannot find release with creation date of 2025-06-01 00:00:00"
    )


def test_find_release_raise_error_asof_str():
    """Test raising an error when we try to use an asof search with a string."""
    with pytest.raises(ValueError) as excinfo:
        lzr.find_release([], "v0.1.0", match="asof")

    assert str(excinfo.value) == (
        "Cannot perform an ``asof`` match using a tag. Please provide a ``datetime.datetime`` value "
        "to perform an ``asof`` match."
    )


def test_find_release_asof_date():
    """Test finding a release using an asof search."""
    releases = [
        lzr.Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
        lzr.Release("v0.2.0", [], datetime(2025, 2, 1, 0, 0, 0)),
        lzr.Release("v0.2.1", [], datetime(2025, 3, 1, 0, 0, 0)),
    ]

    # First, try retrieving a release that predates the earliest
    with pytest.raises(VersionNotFoundError) as excinfo:
        lzr.find_release(releases, datetime(2024, 12, 15, 0, 0, 0), match="asof")

    assert str(excinfo.value) == (
        "Creation date 2024-12-15 00:00:00 predates the earliest release: "
        "'v0.1.0' (2025-01-01 00:00:00)"
    )

    # Next, perform a successful asof search
    out = lzr.find_release(releases, datetime(2025, 2, 15, 0, 0, 0), match="asof")
    assert out == releases[1]

    # Retrieve the latest when we go beyond the last creation date
    out = lzr.find_release(releases, datetime(2025, 6, 1, 0, 0, 0), match="asof")
    assert out == releases[-1]


def test_find_release_invalid_match():
    """Test raising an error when match is invalid."""
    with pytest.raises(ValueError) as excinfo:
        lzr.find_release([], "v0.1.0", match="match-this-idiot")

    assert (
        str(excinfo.value)
        == "Invalid parameterization. Please provide ``exact`` or ``asof`` for ``match``."
    )


def test_dump_release_to_file(tmp_path):
    """Test writing a list of releases to a file."""
    releases = [
        lzr.Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
        lzr.Release("v0.2.0", [], datetime(2025, 2, 1, 0, 0, 0)),
        lzr.Release("v0.2.1", [], datetime(2025, 3, 1, 0, 0, 0)),
    ]
    with open(tmp_path / "releases.json", "wt") as outfile:
        lzr.dump(releases, outfile)

    with open(tmp_path / "releases.json", "rt") as infile:
        data = json.load(infile)

    assert data == [
        {"tag": "v0.1.0", "artifacts": [], "created_at": "2025-01-01T00:00:00"},
        {"tag": "v0.2.0", "artifacts": [], "created_at": "2025-02-01T00:00:00"},
        {"tag": "v0.2.1", "artifacts": [], "created_at": "2025-03-01T00:00:00"},
    ]


def test_dump_release_to_str():
    """Test writing a list of releases to a string."""
    releases = [
        lzr.Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
    ]
    out = lzr.dumps(releases)

    assert (
        out
        == '[{"tag": "v0.1.0", "artifacts": [], "created_at": "2025-01-01T00:00:00"}]'
    )


def test_load_release_from_file(tmp_path):
    """Test loading a release from a JSON file."""
    with open(tmp_path / "releases.json", "wt") as outfile:
        json.dump(
            [
                {
                    "tag": "v0.1.0",
                    "artifacts": [],
                    "created_at": "2025-01-01T00:00:00",
                },
                {"tag": "v0.2.0", "artifacts": [], "created_at": "2025-02-01T00:00:00"},
            ],
            outfile,
        )

    with open(tmp_path / "releases.json", "rt") as infile:
        new_ = lzr.load(infile)

    assert new_ == [
        lzr.Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
        lzr.Release("v0.2.0", [], datetime(2025, 2, 1, 0, 0, 0)),
    ]


def test_load_release_from_str():
    """Test loading a release using a JSON string."""
    mydata = '[{"tag": "v0.1.0", "artifacts": [], "created_at": "2025-01-01T00:00:00"}]'
    new_ = lzr.loads(mydata)

    assert new_ == [
        lzr.Release("v0.1.0", [], datetime(2025, 1, 1, 0, 0, 0)),
    ]


def test_release_from_toml(tmp_path):
    """Test creating a release from a set of repositories."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location, mode="w")
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

    repository.save()

    toml_data = f"""
    [project]
    version = "1.0.0"

    [tool.lazyscribe]
    repositories = ["{repository_location!s}"]
    """

    # create the release
    with time_machine.travel(
        datetime(2025, 6, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        lzr.release_from_toml(toml_data)

    assert (location / "releases.json").is_file()
    with open(location / "releases.json", "rt") as infile:
        releases = lzr.load(infile)

    assert releases == [
        lzr.Release(
            "v1.0.0",
            [["my-data", 1], ["my-features", 0]],
            datetime(2025, 6, 1, 0, 0, 0),
        )
    ]


def test_release_from_toml_existing(tmp_path, caplog):
    """Test adding a new release to an existing release JSON."""
    caplog.set_level(logging.WARNING)
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location, mode="w")
    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 1}], handler="json")
        repository.log_artifact("my-features", [0], handler="json")

    with time_machine.travel(
        datetime(2025, 1, 21, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 2}], handler="json")

    with time_machine.travel(
        datetime(2025, 1, 22, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-features", [0, 1], handler="json")
        repository.log_artifact("my-metadata", {"process_ver": 1.0}, handler="json")

    repository.save()

    # Create an existing release
    with open(location / "releases.json", "wt") as outfile:
        lzr.dump(
            [
                lzr.Release(
                    "v1.0.0",
                    [["my-data", 1], ["my-features", 0]],
                    datetime(2025, 1, 22, 0, 0, 0),
                )
            ],
            outfile,
        )

    # Create a new release
    toml_data = f"""
    [project]
    version = "2.0.0"

    [tool.lazyscribe]
    repositories = ["{repository_location!s}"]
    """

    # create the release
    with time_machine.travel(
        datetime(2025, 6, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        lzr.release_from_toml(toml_data)

    assert (location / "releases.json").is_file()
    with open(location / "releases.json", "rt") as infile:
        releases = lzr.load(infile)

    assert releases == [
        lzr.Release(
            "v1.0.0",
            [["my-data", 1], ["my-features", 0]],
            datetime(2025, 1, 22, 0, 0, 0),
        ),
        lzr.Release(
            "v2.0.0",
            [["my-data", 1], ["my-features", 1], ["my-metadata", 0]],
            datetime(2025, 6, 1, 0, 0, 0),
        ),
    ]

    # Try creating the same release again
    lzr.release_from_toml(toml_data)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == (
        f"Release 'v2.0.0' already exists for the repository at '{repository_location!s}'. Skipping..."
    )
    assert (location / "releases.json").is_file()
    with open(location / "releases.json", "rt") as infile:
        releases = lzr.load(infile)

    assert releases == [
        lzr.Release(
            "v1.0.0",
            [["my-data", 1], ["my-features", 0]],
            datetime(2025, 1, 22, 0, 0, 0),
        ),
        lzr.Release(
            "v2.0.0",
            [["my-data", 1], ["my-features", 1], ["my-metadata", 0]],
            datetime(2025, 6, 1, 0, 0, 0),
        ),
    ]


def test_release_from_toml_custom(tmp_path):
    """Test creating a release from TOML using a custom version/format."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location, mode="w")
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

    repository.save()

    toml_data = f"""
    [tool.lazyscribe]
    version = "1.0.0"
    repositories = ["{repository_location!s}"]
    """
    toml_data += 'format = "v{year}.{month}.{day}"'

    # create the release
    with time_machine.travel(
        datetime(2025, 6, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        lzr.release_from_toml(toml_data)

    assert (location / "releases.json").is_file()
    with open(location / "releases.json", "rt") as infile:
        releases = lzr.load(infile)

    assert releases == [
        lzr.Release(
            "v2025.6.1",
            [["my-data", 1], ["my-features", 0]],
            datetime(2025, 6, 1, 0, 0, 0),
        )
    ]
