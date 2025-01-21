"""Test the repository class."""

import json
import sys
import warnings
import zoneinfo
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import time_machine

from lazyscribe.artifacts.base import Artifact
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

    with pytest.raises(RuntimeError):
        repository.log_artifact("name", [1, 2, 3], handler="json")

    assert len(repository.artifacts) == 4

    with pytest.raises(RuntimeError):
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

    assert "my-dict" in repository_read
    assert "my-dict2" in repository_read
    assert "my-dict3" not in repository_read

    # Non-existing artifact raises error
    with pytest.raises(ValueError):
        repository_read.load_artifact("my-dict3")


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
    assert (location / expected_fname).is_file()

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
