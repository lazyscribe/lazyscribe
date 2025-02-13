"""Test the project class."""

import json
import warnings
import zoneinfo
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import fsspec
import pytest
import time_machine

from lazyscribe import Project
from lazyscribe.experiment import Experiment, ReadOnlyExperiment
from lazyscribe.test import ReadOnlyTest, Test
from tests.conftest import TestArtifact

CURR_DIR = Path(__file__).resolve().parent
DATA_DIR = CURR_DIR / "data"


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
@pytest.mark.parametrize(
    "project_kwargs",
    [
        {"author": "root"},
        {
            "author": "root",
            "fpath": "file://" + (DATA_DIR / "external_fs_project.json").as_posix(),
        },
    ],
)
def test_logging_experiment(project_kwargs):
    """Test logging an experiment to a project."""
    project = Project(**project_kwargs)
    today = datetime.now()
    with project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)

    assert len(project.experiments) == 1
    assert isinstance(project.experiments[0], Experiment)
    assert project.experiments[0].to_dict() == {
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
        "tests": [],
        "tags": [],
    }
    assert project["my-experiment"] == project.experiments[0]
    assert (
        project[f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}"]
        == project.experiments[0]
    )
    with pytest.raises(KeyError):
        project["not a real experiment"]


def test_not_logging_experiment():
    """Test not logging an experiment when raising an error."""
    project = Project(author="root")
    with pytest.raises(ValueError), project.log(name="My experiment") as exp:
        raise ValueError("An error.")
        exp.log_metric("name", 0.5)

    assert len(project.experiments) == 0


def test_not_logging_experiment_readonly():
    """Test trying to log an experiment in read only mode."""
    project = Project(fpath=DATA_DIR / "project.json", mode="r")

    with pytest.raises(RuntimeError), project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)

        assert len(project.experiments) == 0


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_save_project(tmp_path):
    """Test saving a project to an output JSON."""
    location = tmp_path / "my-project"
    location.mkdir()
    project_location = location / "project.json"
    today = datetime.now()
    project = Project(fpath=project_location, author="root")
    with project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)
        with exp.log_test("My test") as test:
            test.log_metric("name-subpop", 0.3)
            test.log_parameter("features", ["col3", "col4"])

    project.save()
    assert project_location.is_file()

    with open(project_location) as infile:
        serialized = json.load(infile)

    assert serialized == [
        {
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
                {
                    "name": "My test",
                    "description": None,
                    "metrics": {"name-subpop": 0.3},
                    "parameters": {"features": ["col3", "col4"]},
                }
            ],
            "tags": [],
        }
    ]


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_save_project_artifact(tmp_path):
    """Test saving a project with an artifact."""
    location = tmp_path / "my-project"
    location.mkdir()
    project_location = location / "project.json"
    today = datetime.now()

    project = Project(fpath=project_location, author="root")
    with project.log(name="My experiment") as exp:
        exp.log_artifact(name="features", value=[0, 1, 2], handler="json")

    project.save()

    assert project_location.is_file()

    features_fname = f"features-{today.strftime('%Y%m%d%H%M%S')}.json"
    assert (
        location / f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}" / features_fname
    ).is_file()

    with open(location / exp.path / features_fname) as infile:
        artifact = json.load(infile)

    assert artifact == [0, 1, 2]


@patch("lazyscribe.artifacts.joblib.importlib_version", side_effect=["1.2.2", "0.0.0"])
def test_save_project_artifact_failed_validation(mock_version, tmp_path):
    """Test saving and loading project with an artifact."""
    location = tmp_path / "my-project"
    location.mkdir()
    project_location = location / "project.json"
    today = datetime.now()

    datasets = pytest.importorskip("sklearn.datasets")
    svm = pytest.importorskip("sklearn.svm")

    project = Project(fpath=project_location, author="root")
    with project.log(name="My experiment") as exp:
        # Fit a basic estimator
        X, y = datasets.make_classification(n_samples=100, n_features=10)
        estimator = svm.SVC(kernel="linear")
        estimator.fit(X, y)
        exp.log_artifact(name="estimator", value=estimator, handler="joblib")

    project.save()

    assert project_location.is_file()
    assert (
        location
        / f"my-experiment-{exp.last_updated.strftime('%Y%m%d%H%M%S')}"
        / f"estimator-{exp.last_updated.strftime('%Y%m%d%H%M%S')}.joblib"
    ).is_file()

    # Reload project and validate experiment
    with pytest.raises(RuntimeError):
        project2 = Project(project_location, mode="r")
        exp2 = project2["my-experiment"]
        model_load = exp2.load_artifact(name="estimator")


def test_save_project_artifact_multi_experiment(tmp_path):
    """Test running save on a project twice with multiple experiments and artifacts.

    The goal of this test is to ensure that an experiment opened in read-only mode or
    one that has not been updated does not result in the file being overwritten on the filesystem.
    """
    location = tmp_path / "my-project"
    location.mkdir()
    project_location = location / "project.json"

    project = Project(fpath=project_location, author="root")
    with project.log(name="My first experiment") as exp:
        exp.log_artifact(name="features", value=[0, 1, 2], handler="json")
    project.save()

    # Reload the project in append-mode and log another experiment
    reload_project = Project(fpath=project_location, mode="a", author="root")
    with reload_project.log(name="My second experiment") as exp:
        exp.log_artifact(name="features", value=[3, 4, 5], handler="json")
    reload_project.save()

    # Check that the first experiment artifact was not overwritten
    fs = fsspec.filesystem("file")
    first_exp = project["my-first-experiment"]
    second_exp = reload_project["my-second-experiment"]
    assert (
        datetime.fromtimestamp(
            fs.info(
                location
                / first_exp.path
                / f"features-{first_exp.last_updated.strftime('%Y%m%d%H%M%S')}.json"
            )["created"]
        )
        < second_exp.created_at
    )

    # Reload the project in editable mode and add another experiment
    final_project = Project(fpath=project_location, mode="w+", author="root")
    with final_project.log(name="My third experiment") as exp:
        exp.log_artifact(name="features", value=[6, 7, 8], handler="json")
    final_project.save()

    # Check that the first and second experiment artifacts were not overwritten
    assert (
        datetime.fromtimestamp(
            fs.info(
                location
                / first_exp.path
                / f"features-{first_exp.last_updated.strftime('%Y%m%d%H%M%S')}.json"
            )["created"]
        )
        < second_exp.created_at
    )

    assert (
        datetime.fromtimestamp(
            fs.info(
                location
                / second_exp.path
                / f"features-{second_exp.last_updated.strftime('%Y%m%d%H%M%S')}.json"
            )["created"]
        )
        < final_project["my-third-experiment"].created_at
    )


def test_save_project_artifact_updated(tmp_path):
    """Test running save twice with an updated experiment.

    The goal of this test is to ensure that an artifact is not overwritten unnecessarily.
    """
    location = tmp_path / "my-project"
    location.mkdir()
    project_location = location / "project.json"

    project = Project(fpath=project_location, author="root")
    with project.log(name="My experiment") as exp:
        exp.log_artifact(name="features", value=[0, 1, 2], handler="json")

    project.save()

    # Re-open the project in editable mode
    new_project = Project(fpath=project_location, mode="w+", author="root")
    new_project["my-experiment"].log_artifact(
        name="feature_names", value=["a", "b", "c"], handler="json"
    )
    new_project.save()

    fs = fsspec.filesystem("file")
    experiment = project["my-experiment"]
    assert (
        datetime.fromtimestamp(
            fs.info(
                location
                / experiment.path
                / f"features-{experiment.last_updated.strftime('%Y%m%d%H%M%S')}.json"
            )["created"]
        )
        < new_project["my-experiment"].last_updated
    )


def test_load_project():
    """Test loading a project back into python."""
    project = Project(fpath=DATA_DIR / "project.json", mode="w+")

    expected = Experiment(
        name="My experiment",
        project=DATA_DIR / "project.json",
        author="root",
        metrics={"name": 0.5},
        created_at=datetime(2022, 1, 1, 9, 30, 0),
        last_updated=datetime(2022, 1, 1, 9, 30, 0),
        tests=[
            Test(
                name="My test",
                metrics={"name-subpop": 0.3},
                parameters={"param": "value"},
            )
        ],
    )

    assert project.experiments == [expected]


def test_load_project_edit(tmp_path):
    """Test loading a project and editing an experiment."""
    location = tmp_path / "my-location"
    location.mkdir()
    project_location = location / "project.json"
    project = Project(fpath=project_location, author="root")
    with project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)

    project.save()

    # Load the project back
    project = Project(fpath=project_location, mode="w+", author="friend")
    exp = project["my-experiment"]
    last_updated = exp.last_updated
    exp.log_metric("name", 0.6)
    project.save()

    assert exp.last_updated > last_updated
    assert exp.last_updated_by == "friend"


def test_load_project_readonly():
    """Test loading a project in read-only or append mode."""
    project = Project(fpath=DATA_DIR / "project.json", mode="r")

    expected = ReadOnlyExperiment(
        name="My experiment",
        project=DATA_DIR / "project.json",
        author="root",
        metrics={"name": 0.5},
        created_at=datetime(2022, 1, 1, 9, 30, 0),
        last_updated=datetime(2022, 1, 1, 9, 30, 0),
        tests=[
            ReadOnlyTest(
                name="My test",
                metrics={"name-subpop": 0.3},
                parameters={"param": "value"},
            )
        ],
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
                last_updated=datetime(2022, 1, 1, 9, 30, 0),
            )
        },
    )

    assert project.experiments == [expected]


def test_merge_append():
    """Test merging a project with one that has an extra experiment."""
    current = Project(fpath=DATA_DIR / "project.json", mode="r")
    newer = Project(fpath=DATA_DIR / "merge_append.json", mode="r")

    new = current.merge(newer)

    assert new.experiments == [
        ReadOnlyExperiment(
            name="My experiment",
            project=DATA_DIR / "project.json",
            author="root",
            metrics={"name": 0.5},
            created_at=datetime(2022, 1, 1, 9, 30, 0),
            last_updated=datetime(2022, 1, 1, 9, 30, 0),
            tests=[
                ReadOnlyTest(
                    name="My test",
                    metrics={"name-subpop": 0.3},
                    parameters={"param": "value"},
                )
            ],
        ),
        ReadOnlyExperiment(
            name="My second experiment",
            project=DATA_DIR / "merge_append.json",
            author="root",
            parameters={"features": ["col1", "col2"]},
            created_at=datetime(2022, 1, 1, 10, 30, 0),
            last_updated=datetime(2022, 1, 1, 10, 30, 0),
        ),
    ]


def test_merge_distinct():
    """Test merging two projects with the no overlapping data."""
    current = Project(fpath=DATA_DIR / "project.json", mode="r")
    newer = Project(fpath=DATA_DIR / "merge_distinct.json", mode="r")

    new = current.merge(newer)

    assert new.experiments == [
        ReadOnlyExperiment(
            name="My experiment",
            project=DATA_DIR / "project.json",
            author="root",
            metrics={"name": 0.5},
            created_at=datetime(2022, 1, 1, 9, 30, 0),
            last_updated=datetime(2022, 1, 1, 9, 30, 0),
            tests=[
                ReadOnlyTest(
                    name="My test",
                    metrics={"name-subpop": 0.3},
                    parameters={"param": "value"},
                )
            ],
        ),
        ReadOnlyExperiment(
            name="My second experiment",
            project=DATA_DIR / "merge_distinct.json",
            author="root",
            parameters={"features": ["col1", "col2"]},
            created_at=datetime(2022, 1, 1, 10, 30, 0),
            last_updated=datetime(2022, 1, 1, 10, 30, 0),
        ),
    ]


def test_merge_update():
    """Test merging projects with an updated experiment."""
    current = Project(fpath=DATA_DIR / "project.json", mode="r")
    newer = Project(fpath=DATA_DIR / "merge_update.json", mode="r")

    new = current.merge(newer)

    assert new.experiments == [
        ReadOnlyExperiment(
            name="My experiment",
            project=DATA_DIR / "merge_update.json",
            author="root",
            last_updated_by="friend",
            metrics={"name": 0.5},
            parameters={"features": ["col1", "col2", "col3"]},
            created_at=datetime(2022, 1, 1, 9, 30, 0),
            last_updated=datetime(2022, 1, 10, 9, 30, 0),
            tests=[
                ReadOnlyTest(
                    name="My test",
                    metrics={"name-subpop": 0.3},
                    parameters={"param": "value"},
                )
            ],
        ),
        ReadOnlyExperiment(
            name="My second experiment",
            project=DATA_DIR / "merge_update.json",
            author="root",
            parameters={"features": ["col1", "col2"]},
            created_at=datetime(2022, 1, 1, 10, 30, 0),
            last_updated=datetime(2022, 1, 1, 10, 30, 0),
        ),
    ]


def test_to_tabular():
    """Test converting a project to a pandas-ready list."""
    project = Project(fpath=DATA_DIR / "merge_update.json", mode="r")
    experiments, tests = project.to_tabular()

    assert experiments == [
        {
            ("name", ""): "My experiment",
            ("author", ""): "root",
            ("last_updated_by", ""): "friend",
            ("metrics", "name"): 0.5,
            ("created_at", ""): "2022-01-01T09:30:00",
            ("last_updated", ""): "2022-01-10T09:30:00",
            ("short_slug", ""): "my-experiment",
            ("slug", ""): "my-experiment-20220101093000",
        },
        {
            ("name", ""): "My second experiment",
            ("author", ""): "root",
            ("last_updated_by", ""): "root",
            ("created_at", ""): "2022-01-01T10:30:00",
            ("last_updated", ""): "2022-01-01T10:30:00",
            ("short_slug", ""): "my-second-experiment",
            ("slug", ""): "my-second-experiment-20220101103000",
        },
    ]

    assert tests == [
        {
            ("experiment_name", ""): "My experiment",
            ("experiment_short_slug", ""): "my-experiment",
            ("experiment_slug", ""): "my-experiment-20220101093000",
            ("test", ""): "My test",
            ("description", ""): None,
            ("metrics", "name-subpop"): 0.3,
            ("parameters", "param"): "value",
        }
    ]


def test_filter_project():
    """Test iterating through experiments based on a filter."""
    project = Project(fpath=DATA_DIR / "merge_update.json", mode="r")
    out = list(project.filter(func=lambda x: x.last_updated_by == "friend"))

    expected = [
        ReadOnlyExperiment(
            name="My experiment",
            project=DATA_DIR / "merge_update.json",
            author="root",
            last_updated_by="friend",
            metrics={"name": 0.5},
            parameters={"features": ["col1", "col2", "col3"]},
            created_at=datetime(2022, 1, 1, 9, 30, 0),
            last_updated=datetime(2022, 1, 10, 9, 30, 0),
            tests=[
                ReadOnlyTest(
                    name="My test",
                    metrics={"name-subpop": 0.3},
                    parameters={"param": "value"},
                )
            ],
        ),
    ]

    assert out == expected


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_save_project_artifact_output_only(tmp_path):
    """Test saving a project with an output only artifact."""
    location = tmp_path / "my-project"
    location.mkdir()
    project_location = location / "project.testartifact"
    today = datetime.now()

    project = Project(fpath=project_location, author="root")
    with (
        project.log(name="My experiment") as exp,
        warnings.catch_warnings(record=True) as w,
    ):
        warnings.simplefilter("always")
        exp.log_artifact(name="features", value=[0, 1, 2], handler="testartifact")
        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert (
            "Artifact 'features' is added. It is not meant to be read back as Python Object"
            in str(w[-1].message)
        )
        assert isinstance(exp.artifacts[0], TestArtifact)
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
                    "fname": f"features-{today.strftime('%Y%m%d%H%M%S')}.testartifact",
                    "handler": "testartifact",
                    "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
                    "version": 0,
                }
            ],
            "tests": [],
            "tags": [],
        }

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        project.save()

        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert (
            "Artifact 'features' is added. It is not meant to be read back as Python Object"
            in str(w[-1].message)
        )

    assert project_location.is_file()
    assert (
        location
        / f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}"
        / f"features-{today.strftime('%Y%m%d%H%M%S')}.testartifact"
    ).is_file()
