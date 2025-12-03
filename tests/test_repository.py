"""Test the repository class."""

import difflib
import json
import logging
import warnings
import zoneinfo
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import time_machine

from lazyscribe.artifacts.base import Artifact
from lazyscribe.exception import (
    ArtifactLoadError,
    ReadOnlyError,
    SaveError,
    VersionNotFoundError,
)
from lazyscribe.repository import Repository
from tests.conftest import TestArtifact

CURR_DIR = Path(__file__).resolve().parent
DATA_DIR = CURR_DIR / "repository_data"


def test_logging_repository():
    """Test logging an artifact to a repository."""
    repository = Repository(
        "file://" + (DATA_DIR / "external_fs_repository.json").as_posix(),
    )
    repository.log_artifact("my-dict", {"a": 1}, handler="json")
    assert len(repository.artifacts) == 1
    assert isinstance(repository.artifacts[0], Artifact)
    assert repository["my-dict"] == repository.artifacts[0]
    with pytest.raises(KeyError):
        repository["not a real artifact"]


def test_readonly():
    """Test trying to log an artifact and save in read only mode."""
    repository = Repository(fpath=DATA_DIR / "repository.json", mode="r")

    with pytest.raises(ReadOnlyError):
        repository.log_artifact("name", [1, 2, 3], handler="json")

    assert len(repository.artifacts) == 4

    with pytest.raises(ReadOnlyError):
        repository.save()

    assert len(repository.artifacts) == 4


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_save_repository(tmp_path):
    """Test saving repository to output JSON."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
    repository.log_artifact("my-dict", {"a": 1}, handler="json")

    repository.save()

    assert repository["my-dict"].dirty is False
    assert repository_location.is_file()

    with open(repository_location) as infile:
        serialized = json.load(infile)

    expected_fname = "my-dict-20250120132330.json"
    assert serialized == [
        {
            "created_at": "2025-01-20T13:23:30",
            "fname": expected_fname,
            "handler": "json",
            "name": "my-dict",
            "version": 0,
        },
    ]

    repository_read = Repository(repository_location, "r")
    artifact_loaded = repository_read.load_artifact("my-dict")
    with open(location / "my-dict" / expected_fname) as infile:
        artifact_read = json.load(infile)
    assert artifact_loaded == artifact_read == {"a": 1}


def test_save_repository_transaction(tmp_path):
    """Test failing to save a repository due to a SaveError."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
    repository.log_artifact(name="should-not-work", value=int, handler="json")

    with pytest.raises(SaveError):
        repository.save()

    assert not repository_location.is_file()


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_update_repository_transaction(tmp_path):
    """Test failing to update a repository due to a SaveError."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
    repository.log_artifact("my-dict", {"a": 1}, handler="json")

    repository.save()

    repository_w = Repository(repository_location, mode="w+")
    repository_w.log_artifact(name="should-not-work", value=int, handler="json")

    with pytest.raises(SaveError):
        repository_w.save()

    # Read in the repository, compare it to the first version
    repository_r = Repository(repository_location, mode="r")

    assert repository_r.artifacts == repository.artifacts


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_save_repository_multi(tmp_path):
    """Test saving a repository, reading it in, logging, saving again."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
    repository.log_artifact("my-dict", {"a": 1}, handler="json")

    repository.save()

    assert repository["my-dict"].dirty is False
    assert repository_location.is_file()

    # Read in the repository again and log a separate artifact
    repository_read = Repository(repository_location, mode="w+")
    repository_read.log_artifact("my-dict-2", {"b": 2}, handler="json")

    assert repository_read["my-dict"].dirty is False
    assert repository_read["my-dict-2"].dirty is True

    repository_read.save()

    assert repository_read["my-dict"].dirty is False
    with open(repository_location) as infile:
        serialized = json.load(infile)

    assert serialized == [
        {
            "created_at": "2025-01-20T13:23:30",
            "fname": "my-dict-20250120132330.json",
            "handler": "json",
            "name": "my-dict",
            "version": 0,
        },
        {
            "created_at": "2025-01-20T13:23:30",
            "fname": "my-dict-2-20250120132330.json",
            "handler": "json",
            "name": "my-dict-2",
            "version": 0,
        },
    ]

    artifact_loaded = repository_read.load_artifact("my-dict")
    with open(location / "my-dict" / "my-dict-20250120132330.json") as infile:
        artifact_read = json.load(infile)

    assert artifact_loaded == artifact_read == {"a": 1}

    artifact_loaded = repository_read.load_artifact("my-dict-2")
    with open(location / "my-dict-2" / "my-dict-2-20250120132330.json") as infile:
        artifact_read = json.load(infile)

    assert artifact_read == artifact_loaded == {"b": 2}


def test_save_repository_multiple_artifact(tmp_path):
    """Test saving repository with multiple artifacts."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-dict", {"a": 1}, handler="json")
        repository.log_artifact("my-dict2", {"b": 2}, handler="json")

    with time_machine.travel(
        datetime(2025, 1, 21, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-dict", {"a": 1, "d": 2}, handler="json")
        repository.save()

    assert repository_location.is_file()

    with open(repository_location) as infile:
        serialized = json.load(infile)

    expected_my_dict_fname0 = "my-dict-20250120132330.json"
    expected_my_dict_fname1 = "my-dict-20250121132330.json"
    expected_my_dict2_fname = "my-dict2-20250120132330.json"
    assert serialized == [
        {
            "created_at": "2025-01-20T13:23:30",
            "fname": expected_my_dict_fname0,
            "handler": "json",
            "name": "my-dict",
            "version": 0,
        },
        {
            "created_at": "2025-01-20T13:23:30",
            "fname": expected_my_dict2_fname,
            "handler": "json",
            "name": "my-dict2",
            "version": 0,
        },
        {
            "created_at": "2025-01-21T13:23:30",
            "fname": expected_my_dict_fname1,
            "handler": "json",
            "name": "my-dict",
            "version": 1,
        },
    ]
    my_dict_dir = location / "my-dict"
    my_dict2_dir = location / "my-dict2"
    with open(my_dict_dir / expected_my_dict_fname0) as infile:
        my_dict_v0_read = json.load(infile)
    with open(my_dict_dir / expected_my_dict_fname1) as infile:
        my_dict_v1_read = json.load(infile)
    with open(my_dict2_dir / expected_my_dict2_fname) as infile:
        my_dict2_read = json.load(infile)

    repository_read = Repository(repository_location, "r")
    my_dict_v0_load_int = repository_read.load_artifact("my-dict", version=0)
    my_dict_v0_load_dt = repository_read.load_artifact(
        "my-dict",
        version=datetime(2025, 1, 20, 13, 23, 30),
    )
    my_dict_v0_load_str = repository_read.load_artifact(
        "my-dict",
        version="2025-01-20T13:23:30",
    )
    assert (
        my_dict_v0_load_int
        == my_dict_v0_load_dt
        == my_dict_v0_read
        == my_dict_v0_load_str
        == {"a": 1}
    )

    my_dict_v1_load_most_recent = repository_read.load_artifact("my-dict")
    my_dict_v1_load_int = repository_read.load_artifact("my-dict", version=1)
    my_dict_v1_load_dt = repository_read.load_artifact(
        "my-dict", version=datetime(2025, 1, 21, 13, 23, 30)
    )
    my_dict_v1_load_str = repository_read.load_artifact(
        "my-dict",
        version="2025-01-21T13:23:30",
    )
    assert (
        my_dict_v1_load_most_recent
        == my_dict_v1_load_int
        == my_dict_v1_load_dt
        == my_dict_v1_read
        == my_dict_v1_load_str
        == {"a": 1, "d": 2}
    )

    my_dict2_load_most_recent = repository_read.load_artifact("my-dict2")
    my_dict2_load_int = repository_read.load_artifact("my-dict2", version=0)
    my_dict2_load_dt = repository_read.load_artifact(
        "my-dict2", version=datetime(2025, 1, 20, 13, 23, 30)
    )
    my_dict2_load_str = repository_read.load_artifact(
        "my-dict2", version="2025-01-20T13:23:30"
    )

    assert (
        my_dict2_load_most_recent
        == my_dict2_load_int
        == my_dict2_load_dt
        == my_dict2_load_str
        == my_dict2_read
        == {"b": 2}
    )

    # Test getting nonexisting version raises error

    with pytest.raises(VersionNotFoundError):
        repository_read.load_artifact("my-dict", version=2)
    with pytest.raises(VersionNotFoundError):
        repository_read.load_artifact("my-dict", version="2025-01-22T12:23:32")
    with pytest.raises(VersionNotFoundError):
        repository_read.load_artifact(
            "my-dict", version=datetime(2025, 1, 22, 13, 23, 30)
        )
    with pytest.raises(VersionNotFoundError):
        repository_read.load_artifact(
            "my-dict2", version=datetime(2025, 1, 22, 13, 23, 30)
        )
    with pytest.raises(VersionNotFoundError):
        repository_read.load_artifact("my-dict2", version=1)
    with pytest.raises(VersionNotFoundError):
        repository_read.load_artifact("my-dict2", version="2025-01-22T12:23:32")

    assert "my-dict" in repository_read
    assert "my-dict2" in repository_read
    assert "my-dict3" not in repository_read

    # Non-existing artifact raises error
    with pytest.raises(ValueError):
        repository_read.load_artifact("my-dict3")


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_save_repository_artifact_failed_validation(tmp_path):
    """Test saving and loading repository with an artifact."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    datasets = pytest.importorskip("sklearn.datasets")
    svm = pytest.importorskip("sklearn.svm")

    repository = Repository(fpath=repository_location)
    # Fit a basic estimator
    X, y = datasets.make_classification(n_samples=100, n_features=10)
    estimator = svm.SVC(kernel="linear")
    estimator.fit(X, y)
    repository.log_artifact(name="estimator", value=estimator, handler="pickle")
    repository.save()

    assert repository_location.is_file()
    assert (location / "estimator" / "estimator-20250120132330.pkl").is_file()

    # Reload repository and validate experiment
    with (
        pytest.raises(ArtifactLoadError),
        patch("lazyscribe.artifacts.pickle.sys.version_info") as mock_version,
    ):
        mock_version.return_value = (3, 9)
        repository2 = Repository(repository_location, mode="r")
        repository2.load_artifact(name="estimator")


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_repository_artifact_output_only(tmp_path):
    """Test saving a repository with an output only artifact."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.testartifact"

    repository = Repository(fpath=repository_location)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        repository.log_artifact(
            name="features", value=[0, 1, 2], handler="testartifact"
        )
        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert (
            "Artifact 'features' is added. It is not meant to be read back as Python Object"
            in str(w[-1].message)
        )
        assert isinstance(repository.artifacts[0], TestArtifact)

        expected_fname = "features-20250120132330.testartifact"
        assert list(repository) == [
            {
                "created_at": "2025-01-20T13:23:30",
                "fname": expected_fname,
                "handler": "testartifact",
                "name": "features",
                "version": 0,
            }
        ]

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        repository.save()

        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert (
            "Artifact 'features' is added. It is not meant to be read back as Python Object"
            in str(w[-1].message)
        )

    assert repository_location.is_file()
    assert (location / "features" / expected_fname).is_file()

    # Test loading a read-only artifact

    repository_read = Repository(fpath=repository_location, mode="r")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        repository_read.load_artifact("features")
        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert "Artifact 'features' is not the original Python Object" in str(
            w[-1].message
        )


def test_invalid_match_strategy():
    """Test raising an error with an invalid value for ``match``."""
    repository = Repository()
    repository.log_artifact("my-dict", {"a": 1}, handler="json")

    with pytest.raises(ValueError):
        repository._search_artifact_versions(
            "my-dict", version=datetime(2025, 1, 1), match="fake"
        )


def test_repository_asof_search(tmp_path):
    """Test retrieving artifacts using ``asof``."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)

    # Log artifacts using time-travel to get different creation dates
    with time_machine.travel(
        datetime(2025, 1, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        repository.log_artifact("my-dict", {"a": 1}, handler="json")
    with time_machine.travel(
        datetime(2025, 2, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        repository.log_artifact("my-dict", {"a": 2}, handler="json")
    with time_machine.travel(
        datetime(2025, 3, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        repository.log_artifact("my-dict", {"a": 3}, handler="json")

    repository.save()

    # Try loading with date before first artifact
    with pytest.raises(VersionNotFoundError) as exc_info:
        repository.load_artifact(
            name="my-dict", version=datetime(2024, 12, 31), match="asof"
        )

        assert str(exc_info.value) == (
            "Version 2024-12-31T00:00:00 predates the earliest version 2025-01-01T00:00:00"
        )

    # Check loading an exact match
    art = repository.load_artifact(
        name="my-dict", version=datetime(2025, 1, 1), match="asof"
    )

    assert art == repository.load_artifact(name="my-dict", version=0)

    # Check loading as of an intermediate date
    art = repository.load_artifact(
        name="my-dict", version=datetime(2025, 1, 15), match="asof"
    )

    assert art == repository.load_artifact(name="my-dict", version=datetime(2025, 1, 1))

    # Check loading the latest
    art = repository.load_artifact(
        name="my-dict", version=datetime(2025, 3, 15), match="asof"
    )

    assert art == repository.load_artifact(name="my-dict", version=datetime(2025, 3, 1))


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_retrieve_artifact_meta():
    """Test retrieving artifact metadata."""
    repository = Repository()
    repository.log_artifact("my-dict", {"a": 1}, handler="json")

    data = repository.get_artifact_metadata("my-dict")

    assert data == {
        "created_at": "2025-01-20T13:23:30",
        "fname": "my-dict-20250120132330.json",
        "handler": "json",
        "name": "my-dict",
        "version": 0,
    }


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_version_diff_dirty():
    """Test raising an error when trying to compare artifacts that aren't on disk."""
    repository = Repository()
    repository.log_artifact("my-data", {"a": 1}, handler="json")
    repository.log_artifact("my-data", {"a": 2}, handler="json")

    with pytest.raises(ArtifactLoadError):
        repository.get_version_diff("my-data", 0)


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_version_diff_binary(tmp_path):
    """Test raising an error when trying to compare binary artifacts."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
    repository.log_artifact("my-data", {"a": 1}, handler="pickle")
    repository.save()
    repository.log_artifact("my-data", {"a": 2}, handler="pickle")
    repository.save()

    with pytest.raises(ValueError):
        repository.get_version_diff("my-data", 0)


def test_version_diff_latest(tmp_path):
    """Test comparing a single version against the latest available."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", {"a": 1}, handler="json", indent=4)

    with time_machine.travel(
        datetime(2025, 1, 21, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", {"a": 2}, handler="json", indent=4)
        repository.save()

    out = repository.get_version_diff("my-data", 0)
    expected = "\n".join(
        difflib.unified_diff(
            json.dumps({"a": 1}, indent=4).splitlines(),
            json.dumps({"a": 2}, indent=4).splitlines(),
        )
    )

    assert out == expected


def test_version_diff_specified(tmp_path):
    """Test comparing specific versions against each other."""
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 1}], handler="json", indent=4)

    with time_machine.travel(
        datetime(2025, 1, 21, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 2}], handler="json", indent=4)

    with time_machine.travel(
        datetime(2025, 1, 22, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact(
            "my-data", [{"a": 2}, {"a": 1}], handler="json", indent=4
        )
        repository.save()

    out = repository.get_version_diff("my-data", (0, 2))
    expected = "\n".join(
        difflib.unified_diff(
            json.dumps([{"a": 1}], indent=4).splitlines(),
            json.dumps([{"a": 2}, {"a": 1}], indent=4).splitlines(),
        )
    )

    assert out == expected


def test_version_diff_identical(tmp_path, caplog):
    """Test raising a warning when a single version is accidentally specified."""
    caplog.set_level = logging.WARNING
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 1}], handler="json", indent=4)

    with time_machine.travel(
        datetime(2025, 1, 21, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-data", [{"a": 2}], handler="json", indent=4)

    with time_machine.travel(
        datetime(2025, 1, 22, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact(
            "my-data", [{"a": 2}, {"a": 1}], handler="json", indent=4
        )
        repository.save()

    out = repository.get_version_diff("my-data", 2)

    assert out == ""
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "Only version '2' was supplied for comparison"


def test_repository_filter(tmp_path, caplog):
    """Test filtering a repository."""
    caplog.set_level = logging.WARNING
    location = tmp_path / "my-repository"
    location.mkdir()
    repository_location = location / "repository.json"

    repository = Repository(repository_location)
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
        repository.log_artifact("my-features", [0, 1], handler="json")

    with time_machine.travel(
        datetime(2025, 1, 22, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC"))
    ):
        repository.log_artifact("my-metadata", {"process_ver": 1.0}, handler="json")

    repository.save()

    # Filter the repository
    repository = Repository(repository_location, mode="r")
    new_ = repository.filter(datetime(2025, 1, 21, 0, 0, 0))

    assert len(new_.artifacts) == 2
    assert "my-metadata" not in new_
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert (
        caplog.records[0].message
        == "Artifact 'my-metadata' does not have a version that predates 2025-01-21 00:00:00"
    )
    assert new_["my-data"] == repository._search_artifact_versions("my-data", 0)
    assert new_["my-features"] == repository._search_artifact_versions("my-features", 0)

    # Now, filter the original repository with an explicit list of artifacts and versions
    artifacts_ = [("my-features", 1), ("my-metadata", 0)]
    new_spec_ = repository.filter(artifacts_)

    assert len(new_spec_.artifacts) == 2
    assert "my-data" not in new_spec_
    assert new_spec_["my-features"] == repository._search_artifact_versions(
        "my-features", 1
    )
    assert new_spec_["my-metadata"] == repository._search_artifact_versions(
        "my-metadata", 0
    )
