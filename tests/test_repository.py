"""Test the repository class."""

import json
import sys
import zoneinfo
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import time_machine

from lazyscribe.artifacts.base import Artifact
from lazyscribe.repository import Repository

CURR_DIR = Path(__file__).resolve().parent
DATA_DIR = CURR_DIR / "repository_data"


def test_logging_repository():
    """Test logging an artifact to a repository."""
    repository = Repository(
        "file://" + (DATA_DIR / "external_fs_project.json").as_posix(),
    )
    repository.log_artifact("my-dict", {"a": 1}, handler="json")
    assert len(repository.artifacts) == 1
    assert isinstance(repository.artifacts[0], Artifact)
    assert repository["my-dict"] == repository.artifacts[0]
    with pytest.raises(KeyError):
        repository["not a real artifact"]


def test_not_logging_artifact_readonly():
    repository = Repository(DATA_DIR / "repository.json", mode="r")
    repository.log_artifact("error", {"b": 2}, handler="json")


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
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            "version": 0,
        },
    ]

    repository_read = Repository(repository_location, "r")
    artifact_loaded = repository_read.load_artifact("my-dict")
    with open(location / expected_fname) as infile:
        artifact_read = json.load(infile)
    assert artifact_loaded == artifact_read == {"a": 1}


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
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            "version": 0,
        },
        {
            "created_at": "2025-01-20T13:23:30",
            "fname": expected_my_dict2_fname,
            "handler": "json",
            "name": "my-dict2",
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            "version": 0,
        },
        {
            "created_at": "2025-01-21T13:23:30",
            "fname": expected_my_dict_fname1,
            "handler": "json",
            "name": "my-dict",
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            "version": 1,
        },
    ]

    with open(location / expected_my_dict_fname0) as infile:
        my_dict_v0_read = json.load(infile)
    with open(location / expected_my_dict_fname1) as infile:
        my_dict_v1_read = json.load(infile)
    with open(location / expected_my_dict2_fname) as infile:
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

    with pytest.raises(ValueError):
        repository_read.load_artifact("my-dict", version=2)
    with pytest.raises(ValueError):
        repository_read.load_artifact("my-dict", version="2025-01-22T12:23:32")
    with pytest.raises(ValueError):
        repository_read.load_artifact(
            "my-dict", version=datetime(2025, 1, 22, 13, 23, 30)
        )
    with pytest.raises(ValueError):
        repository_read.load_artifact(
            "my-dict2", version=datetime(2025, 1, 22, 13, 23, 30)
        )
    with pytest.raises(ValueError):
        repository_read.load_artifact("my-dict2", version=1)
    with pytest.raises(ValueError):
        repository_read.load_artifact("my-dict2", version="2025-01-22T12:23:32")


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
@patch("lazyscribe.artifacts.joblib.importlib_version", side_effect=["1.2.2", "0.0.0"])
def test_save_repository_artifact_failed_validation(mock_version, tmp_path):
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
    repository.log_artifact(name="estimator", value=estimator, handler="joblib")
    repository.save()

    assert repository_location.is_file()
    assert (location / "estimator-20250120132330.joblib").is_file()

    # Reload repository and validate experiment
    with pytest.raises(RuntimeError):
        repository2 = Repository(repository_location, mode="r")
        repository2.load_artifact(name="estimator")
