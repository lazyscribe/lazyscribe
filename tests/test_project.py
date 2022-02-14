"""Test the project class."""

from datetime import datetime
from pathlib import Path

from lazyscribe import Project
from lazyscribe.experiment import Experiment, ReadOnlyExperiment
import pytest

CURR_DIR = Path(__file__).resolve().parent
DATA_DIR = CURR_DIR / "data"


def test_logging_experiment():
    """Test logging an experiment to a project."""
    project = Project(author="root")
    today = datetime.now()
    with project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)

    assert len(project.experiments) == 1
    assert isinstance(project.experiments[0], Experiment)
    assert project.experiments[0].to_dict() == {
        "name": "My experiment",
        "author": "root",
        "metrics": {"name": 0.5},
        "parameters": {},
        "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "last_updated": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "dependencies": [],
        "short_slug": "my-experiment",
        "slug": f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}",
    }
    assert project["my-experiment"] == project.experiments[0]
    assert project[f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}"] == project.experiments[0]
    with pytest.raises(KeyError):
        project["not a real experiment"]


def test_not_logging_experiment():
    """Test not logging an experiment when raising an error."""
    project = Project(author="root")
    with pytest.raises(ValueError):
        with project.log(name="My experiment") as exp:
            raise ValueError("An error.")
            exp.log_metric("name", 0.5)

    assert len(project.experiments) == 0


def test_not_logging_experiment_readonly():
    """Test trying to log an experiment in read only mode."""
    project = Project(fpath=DATA_DIR / "project.json", mode="r")

    with pytest.raises(RuntimeError):
        with project.log(name="My experiment") as exp:
            exp.log_metric("name", 0.5)

        assert len(project.experiments) == 0


def test_save_project(tmpdir):
    """Test saving a project to an output JSON."""
    location = tmpdir.mkdir("my-project")
    project = Project(fpath=Path(str(location)) / "project.json", author="root")
    with project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)

    project.save()
    assert (Path(str(location)) / "project.json").is_file()


def test_load_project():
    """Test loading a project back into python."""
    project = Project(fpath=DATA_DIR / "project.json", mode="w+")

    expected = Experiment(
        name="My experiment",
        project=DATA_DIR / "project.json",
        author="root",
        metrics={"name": 0.5},
        created_at=datetime(2022, 1, 1, 9, 30, 0),
        last_updated=datetime(2022, 1, 1, 9, 30, 0)
    )

    assert project.experiments == [expected]


def test_load_project_readonly():
    """Test loading a project in read-only or append mode."""
    project = Project(fpath=DATA_DIR / "project.json", mode="r")

    expected = ReadOnlyExperiment(
        name="My experiment",
        project=DATA_DIR / "project.json",
        author="root",
        metrics={"name": 0.5},
        created_at=datetime(2022, 1, 1, 9, 30, 0),
        last_updated=datetime(2022, 1, 1, 9, 30, 0)
    )

    assert project.experiments == [expected]
    with pytest.raises(RuntimeError):
        project.save()


def test_load_project_dependencies():
    """Test loading a project where an experiment has dependencies."""
    project = Project(fpath=DATA_DIR / "down-project.json", mode="a")

    expected = ReadOnlyExperiment(
        name="My downstream experiment",
        project=DATA_DIR / "down-project.json",
        author="root",
        created_at=datetime(2022, 1, 15, 9, 30, 0),
        last_updated=datetime(2022, 1, 15, 9, 30, 0),
        dependencies={
            "my-experiment": ReadOnlyExperiment(
                name="My experiment",
                project=DATA_DIR / "project.json",
                author="root",
                metrics={"name": 0.5},
                created_at=datetime(2022, 1, 1, 9, 30, 0),
                last_updated=datetime(2022, 1, 1, 9, 30, 0)
            )
        }
    )

    assert project.experiments == [expected]
