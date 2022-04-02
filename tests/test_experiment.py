"""Test the experiment dataclass."""

from datetime import datetime
from pathlib import Path

from attrs.exceptions import FrozenInstanceError
import pytest

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
    with exp.log_test(name="My test") as test:
        test.log_metric("name-subpop", 0.3)

    assert exp.metrics == {"name": 0.5, "name-cv": 0.4}
    assert exp.parameters == {"features": ["col1", "col2"]}
    assert exp.tests == [Test(name="My test", metrics={"name-subpop": 0.3})]


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
        "tests": [
            {"name": "My test", "description": None, "metrics": {"name-subpop": 0.3}}
        ],
    }


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
        "tests": [],
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
