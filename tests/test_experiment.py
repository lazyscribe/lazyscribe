"""Test the experiment dataclass."""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from attrs.exceptions import FrozenInstanceError

from lazyscribe.artifacts import _get_handler
from lazyscribe.experiment import Experiment, ReadOnlyExperiment
from lazyscribe.test import Test


def test_attrs_default():
    """Test any non-trivial experiment attributes."""
    today = datetime.now()
    exp = Experiment(name="My experiment", project=Path("project.json"))

    assert exp.dir == Path(".")
    assert exp.short_slug == "my-experiment"
    assert exp.slug == f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}"
    assert exp.path == Path(".", f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}")


def test_experiment_logging():
    """Test logging metrics and parameters."""
    exp = Experiment(name="My experiment", project=Path("project.json"))
    exp.log_metric("name", 0.5)
    exp.log_metric("name-cv", 0.4)
    exp.log_parameter("features", ["col1", "col2"])
    exp.tag("success")
    with exp.log_test(name="My test") as test:
        test.log_metric("name-subpop", 0.3)

    assert exp.metrics == {"name": 0.5, "name-cv": 0.4}
    assert exp.parameters == {"features": ["col1", "col2"]}
    assert exp.tests == [Test(name="My test", metrics={"name-subpop": 0.3})]
    assert exp.tags == ["success"]

    # Add another tag without overwriting
    exp.tag("huge success")
    assert exp.tags == ["success", "huge success"]

    # Overwrite the tags
    exp.tag("actually a failure", overwrite=True)
    assert exp.tags == ["actually a failure"]


def test_experiment_serialization():
    """Test serializing the experiment to a dictionary."""
    today = datetime.now()
    exp = Experiment(name="My experiment", project=Path("project.json"), author="root")
    exp.log_metric("name", 0.5)
    with exp.log_test(name="My test") as test:
        test.log_metric("name-subpop", 0.3)

    assert exp.to_dict() == {
        "name": "My experiment",
        "author": "root",
        "last_updated_by": "root",
        "metrics": {"name": 0.5},
        "parameters": {},
        "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "last_updated": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "dependencies": [],
        "short_slug": "my-experiment",
        "slug": f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}",
        "artifacts": [],
        "tests": [
            {"name": "My test", "description": None, "metrics": {"name-subpop": 0.3}}
        ],
        "tags": [],
    }


def test_experiment_artifact_logging_basic():
    """Test logging an artifact to the experiment."""
    today = datetime.now()
    exp = Experiment(name="My experiment", project=Path("project.json"), author="root")
    exp.log_artifact(name="features", value=[0, 1, 2], handler="json")
    JSONArtifact = _get_handler("json")
    assert isinstance(exp.artifacts[0], JSONArtifact)
    assert exp.to_dict() == {
        "name": "My experiment",
        "author": "root",
        "last_updated_by": "root",
        "metrics": {},
        "parameters": {},
        "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "last_updated": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "dependencies": [],
        "short_slug": "my-experiment",
        "slug": f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}",
        "artifacts": [
            {
                "name": "features",
                "fname": "features.json",
                "handler": "json",
                "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
                "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            }
        ],
        "tests": [],
        "tags": [],
    }


def test_experiment_artifact_logging_overwrite():
    """Test overwriting an artifact."""
    exp = Experiment(name="My experiment", project=Path("project.json"), author="root")
    exp.log_artifact(name="features", value=[0, 1, 2], handler="json")
    JSONArtifact = _get_handler("json")
    assert isinstance(exp.artifacts[0], JSONArtifact)

    with pytest.raises(RuntimeError):
        exp.log_artifact(name="features", value=[3, 4, 5], handler="json")

    assert exp.artifacts[0].value == [0, 1, 2]

    exp.log_artifact(name="features", value=[3, 4, 5], handler="json", overwrite=True)

    assert exp.artifacts[0].value == [3, 4, 5]


def test_experiment_artifact_load(tmp_path):
    """Test loading an experiment artifact from the disk."""
    location = tmp_path / "my-location"
    location.mkdir()

    exp = Experiment(
        name="My experiment", project=location / "project.json", author="root"
    )
    exp.log_artifact(name="features", value=[0, 1, 2], handler="json")
    # Need to write the artifact to disk
    fpath = exp.dir / exp.path / exp.artifacts[0].fname
    exp.fs.makedirs(exp.dir / exp.path, exist_ok=True)
    with exp.fs.open(fpath, "w") as buf:
        exp.artifacts[0].write(exp.artifacts[0].value, buf)

    assert (location / "my-location" / exp.path / "features.json").is_file()

    out = exp.load_artifact(name="features")

    assert out == [0, 1, 2]


def test_experiment_artifact_load_keyerror(tmp_path):
    """Test trying to load an artifact that doesn't exist."""
    location = tmp_path / "my-location"
    location.mkdir()

    exp = Experiment(
        name="My experiment", project=location / "project.json", author="root"
    )

    with pytest.raises(ValueError):
        exp.load_artifact(name="features")


def test_experiment_artifact_load_validation():
    """Test the handler validation."""
    datasets = pytest.importorskip("sklearn.datasets")
    svm = pytest.importorskip("sklearn.svm")

    # Fit a basic estimator
    X, y = datasets.make_classification(n_samples=100, n_features=10)
    estimator = svm.SVC(kernel="linear")
    estimator.fit(X, y)

    exp = Experiment(name="My experiment", project=Path("project.json"), author="root")
    exp.log_artifact(name="estimator", value=estimator, handler="joblib")

    # Edit the experiment parameters to make sure the validation fails
    exp.artifacts[0].package_version = "0.0.0"

    with pytest.raises(RuntimeError):
        exp.load_artifact(name="estimator")


def test_experiment_serialization_dependencies():
    """Test serializing an experiment with a dependency."""
    today = datetime.now()
    upstream = Experiment(
        name="My experiment", project=Path("other-project.json"), author="root"
    )
    exp = Experiment(
        name="My downstream experiment",
        project=Path("project.json"),
        author="root",
        dependencies={"my-experiment": upstream},
    )

    assert exp.to_dict() == {
        "name": "My downstream experiment",
        "author": "root",
        "last_updated_by": "root",
        "metrics": {},
        "parameters": {},
        "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "last_updated": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "dependencies": [
            f"other-project.json|my-experiment-{today.strftime('%Y%m%d%H%M%S')}"
        ],
        "short_slug": "my-downstream-experiment",
        "slug": f"my-downstream-experiment-{today.strftime('%Y%m%d%H%M%S')}",
        "artifacts": [],
        "tests": [],
        "tags": [],
    }


def test_experiment_comparison():
    """Test comparing two experiments."""
    exp = Experiment(name="My experiment", project=Path("project.json"))
    # Create a second experiment with the same slug and same created_at time
    exp_new = Experiment(
        name="My experiment",
        project=Path("project.json"),
        slug=exp.slug,
        created_at=exp.created_at,
    )

    assert exp_new > exp

    # Create a third experiment with a new slug, same last_updated time, new created_at
    exp_diff = Experiment(
        name="New experiment",
        project=Path("project.json"),
        last_updated=exp.last_updated,
    )

    assert exp_diff > exp


def test_frozen_experiment():
    """Test raising errors with a read-only experiment."""
    exp = ReadOnlyExperiment(name="My experiment", project=Path("project.json"))
    with pytest.raises(FrozenInstanceError):
        exp.name = "Let's change the name"


import warnings


def test_experiment_artifact_log_load_output_only(tmp_path):
    """Test loading an experiment artifact from the disk."""
    location = tmp_path / "my-location"
    location.mkdir()

    exp = Experiment(
        name="My experiment", project=location / "project.json", author="root"
    )
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        exp.log_artifact(name="features", value=[0, 1, 2], handler="testartifact")
        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert (
            "Artifact 'features' is added. It is not meant to be read back as Python Object"
            in str(w[-1].message)
        )

    # Need to write the artifact to disk
    fpath = exp.dir / exp.path / exp.artifacts[0].fname
    exp.fs.makedirs(exp.dir / exp.path, exist_ok=True)
    with exp.fs.open(fpath, "w") as buf:
        exp.artifacts[0].write(exp.artifacts[0].value, buf)

    assert (location / "my-location" / exp.path / "features.testartifact").is_file()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        exp.load_artifact(name="features")

        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert "Artifact 'features' is not the original Python Object" in str(
            w[-1].message
        )
