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
from lazyscribe.exception import ArtifactLoadError, ReadOnlyError
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
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            "version": 0,
        },
    ]

    repository_read = Repository(repository_location, "r")
    artifact_loaded = repository_read.load_artifact("my-dict")
    with open(location / "my-dict" / expected_fname) as infile:
        artifact_read = json.load(infile)
    assert artifact_loaded == artifact_read == {"a": 1}


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
    repository_read = Repository(repository_location, mode="a")
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
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            "version": 0,
        },
        {
            "created_at": "2025-01-20T13:23:30",
            "fname": "my-dict-2-20250120132330.json",
            "handler": "json",
            "name": "my-dict-2",
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
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
    assert (location / "estimator" / "estimator-20250120132330.joblib").is_file()

    # Reload repository and validate experiment
    with pytest.raises(ArtifactLoadError):
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

    art = repository.load_artifact(
        name="my-dict", version=datetime(2025, 1, 15), match="asof"
    )

    assert art == repository.load_artifact(name="my-dict", version=datetime(2025, 1, 1))

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
        "python_version": ".".join(str(i) for i in sys.version_info[:2]),
        "version": 0,
    }
