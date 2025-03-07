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
from lazyscribe.exception import ArtifactLoadError, ReadOnlyError
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

    assert "my-experiment" in project
    assert f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}" in project
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
    assert project["my-experiment"].dirty is True
    with pytest.raises(KeyError):
        project["not a real experiment"]


def test_invalid_project_mode():
    """Test instantiating a project with an invalid mode."""
    with pytest.raises(ValueError):
        _ = Project(author="root", mode="fake-mode")


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
    context_manager = project.log(name="New experiment")
    with pytest.raises(ReadOnlyError):
        _ = context_manager.__enter__()

    context_manager.__exit__(None, None, None)

    assert len(project.experiments) == 1
    assert "new-experiment" not in project


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_save_project(tmp_path):
    """Test saving a project to an output JSON."""
    location = tmp_path / "my-project"
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
    assert project["my-experiment"].dirty is False

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
    project_location = location / "project.json"
    today = datetime.now()

    project = Project(fpath=project_location, author="root")
    with project.log(name="My experiment") as exp:
        exp.log_artifact(name="features", value=[0, 1, 2], handler="json")

    project.save()

    assert project["my-experiment"].dirty is False
    assert project["my-experiment"].artifacts[0].dirty is False
    assert project_location.is_file()

    features_fname = f"features-{today.strftime('%Y%m%d%H%M%S')}.json"
    assert (
        location / f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}" / features_fname
    ).is_file()

    with open(location / exp.path / features_fname) as infile:
        artifact = json.load(infile)

    assert artifact == [0, 1, 2]


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_save_project_artifact_str_path(tmp_path):
    """Test saving a project with an artifact."""
    location = tmp_path / "my-project"
    project_location = str(location / "project.json")
    today = datetime.now()

    project = Project(fpath=project_location, author="root")
    with project.log(name="My experiment") as exp:
        exp.log_artifact(name="features", value=[0, 1, 2], handler="json")

    project.save()

    assert project["my-experiment"].dirty is False
    assert project["my-experiment"].artifacts[0].dirty is False
    assert Path(project_location).is_file()

    features_fname = f"features-{today.strftime('%Y%m%d%H%M%S')}.json"
    assert (
        location / f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}" / features_fname
    ).is_file()

    with open(location / exp.path / features_fname) as infile:
        artifact = json.load(infile)

    assert artifact == [0, 1, 2]


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
@patch("lazyscribe.artifacts.joblib.importlib_version", side_effect=["1.2.2", "0.0.0"])
def test_save_project_artifact_failed_validation(mock_version, tmp_path):
    """Test saving and loading project with an artifact."""
    location = tmp_path / "my-project"
    project_location = location / "project.json"

    datasets = pytest.importorskip("sklearn.datasets")
    svm = pytest.importorskip("sklearn.svm")

    project = Project(fpath=project_location, author="root")
    with project.log(name="My experiment") as exp:
        # Fit a basic estimator
        X, y = datasets.make_classification(n_samples=100, n_features=10)
        estimator = svm.SVC(kernel="linear")
        estimator.fit(X, y)
        exp.log_artifact(name="estimator", value=estimator, handler="joblib")

    assert project["my-experiment"].dirty is True

    project.save()

    assert project["my-experiment"].dirty is False
    assert project["my-experiment"].artifacts[0].dirty is False
    assert project_location.is_file()
    assert (
        location
        / f"my-experiment-{exp.last_updated.strftime('%Y%m%d%H%M%S')}"
        / f"estimator-{exp.last_updated.strftime('%Y%m%d%H%M%S')}.joblib"
    ).is_file()

    # Reload project and validate experiment
    with pytest.raises(ArtifactLoadError):
        project2 = Project(project_location, mode="r")
        exp2 = project2["my-experiment"]
        model_load = exp2.load_artifact(name="estimator")


def test_save_project_artifact_multi_experiment(tmp_path):
    """Test running save on a project twice with multiple experiments and artifacts.

    The goal of this test is to ensure that an experiment opened in read-only mode or
    one that has not been updated does not result in the file being overwritten on the filesystem.

    The logic of the test is that if we manually delete an artifact, it should not re-appear in the
    filesystem.

    This logic works with the JSON handler because you can write a JSON file with `None`
    as the value:

    .. code-block:: python

        from lazyscribe.artifacts.json import JSONArtifact

        art = JSONArtifact.construct(name="mydict")
        with open("test.json", "w") as buf:
            art.write(None, buf)

    So, if the file re-appears, it means that :py:meth:`lazyscribe.artifacts.json.JSONArtifact.write` was
    called without us re-loading the object into memory and without overwriting the artifact in the experiment(s).
    """
    location = tmp_path / "my-project"
    project_location = location / "project.json"

    project = Project(fpath=project_location, author="root")
    with project.log(name="My first experiment") as exp:
        exp.log_artifact(name="features", value=[0, 1, 2], handler="json")
    project.save()

    # Reload the project in append-mode and log another experiment
    reload_project = Project(fpath=project_location, mode="a", author="root")

    assert reload_project["my-first-experiment"].dirty is False

    with reload_project.log(name="My second experiment") as exp:
        exp.log_artifact(name="features", value=[3, 4, 5], handler="json")

    # Manually delete the artifact file
    fs = fsspec.filesystem("file")
    first_art_path = (
        project["my-first-experiment"].path
        / project["my-first-experiment"].artifacts[0].fname
    )
    fs.rm(str(first_art_path))

    reload_project.save()

    # Check that the first experiment artifact was not overwritten -- it should not exist
    assert not first_art_path.is_file()

    # Reload the project in editable mode and add another experiment
    final_project = Project(fpath=project_location, mode="w+", author="root")

    assert final_project["my-first-experiment"].dirty is False
    assert final_project["my-second-experiment"].dirty is False

    with final_project.log(name="My third experiment") as exp:
        exp.log_artifact(name="features", value=[6, 7, 8], handler="json")

    # Manually delete the second artifact file
    second_art_path = (
        reload_project["my-second-experiment"].path
        / reload_project["my-second-experiment"].artifacts[0].fname
    )
    fs.rm(second_art_path)

    final_project.save()

    # Check that the first and second experiment artifacts were not overwritten
    assert not first_art_path.is_file()
    assert not second_art_path.is_file()


def test_save_project_artifact_updated(tmp_path):
    """Test running save twice with an updated experiment.

    The goal of this test is to ensure that an artifact is not overwritten unnecessarily.

    The logic of the test is that if we manually delete an artifact, it should not re-appear in the
    filesystem.

    This logic works with the JSON handler because you can write a JSON file with `None`
    as the value:

    .. code-block:: python

        from lazyscribe.artifacts.json import JSONArtifact

        art = JSONArtifact.construct(name="mydict")
        with open("test.json", "w") as buf:
            art.write(None, buf)

    So, if the file re-appears, it means that :py:meth:`lazyscribe.artifacts.json.JSONArtifact.write` was
    called without us re-loading the object into memory and without overwriting the artifact in the experiment(s).
    """
    location = tmp_path / "my-project"
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

    # Intentionally delete the artifact
    fs = fsspec.filesystem("file")
    art_path = (
        project["my-experiment"].path / project["my-experiment"].artifacts[0].fname
    )
    fs.rm(str(art_path))

    new_project.save()

    # The artifact file should not exist because we manually deleted it and it wasn't overwritten
    assert not art_path.is_file()


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
    project_location = location / "project.json"
    project = Project(fpath=project_location, author="root")
    with project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)

    project.save()

    # Load the project back
    project = Project(fpath=project_location, mode="w+", author="friend")
    exp = project["my-experiment"]

    assert exp.dirty is False

    last_updated = exp.last_updated
    exp.log_metric("name", 0.6)

    assert exp.dirty is True

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
    with pytest.raises(ReadOnlyError):
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
