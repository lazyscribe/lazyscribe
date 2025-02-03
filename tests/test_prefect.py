"""Test the prefect integration."""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from prefect import Flow, Parameter

from lazyscribe.prefect import LazyExperiment, LazyProject

CURR_DIR = Path(__file__).resolve().parent
DATA_DIR = CURR_DIR / "data"


def test_prefect_experiment(tmp_path):
    """Test creating an experiment and logging basic parameters."""
    location = tmp_path / "my-location"
    location.mkdir()

    init_experiment = LazyExperiment()
    with Flow(name="Create experiment") as flow:
        experiment = init_experiment(
            project=location / "project.json", name="My experiment", author="root"
        )
        experiment.log_metric("name", 0.5)
        experiment.log_parameter("param", "value")
        experiment.tag("success")
        experiment.log_artifact(name="features", value=[0, 1, 2], handler="json")
        with experiment.log_test(name="My test") as test:
            test.log_metric("subpop", 0.7)
            test.log_parameter("param", "value")

    assert {tsk.name for tsk in flow.downstream_tasks(experiment)} == {
        "Log experiment metric",
        "Log parameter",
        "Log artifact",
        "Append test",
        "Add tag",
    }
    assert (
        flow.downstream_tasks(flow.get_tasks(name="Log experiment metric")[0]) == set()
    )
    assert flow.downstream_tasks(flow.get_tasks(name="Log parameter")[0]) == set()
    assert {tsk.name for tsk in flow.downstream_tasks(test)} == {
        "Log test metric",
        "Log test parameter",
        "Append test",
    }
    assert {
        tsk.name
        for tsk in flow.downstream_tasks(flow.get_tasks(name="Log test metric")[0])
    } == {"Append test"}

    output = flow.run()
    exp_dict = output.result[experiment].result.to_dict()
    today = datetime.now()

    assert output.is_successful()
    assert exp_dict["name"] == "My experiment"
    assert exp_dict["author"] == "root"
    assert exp_dict["last_updated_by"] == "root"
    assert exp_dict["metrics"] == {"name": 0.5}
    assert exp_dict["parameters"] == {"param": "value"}
    assert exp_dict["created_at"].startswith(today.strftime("%Y-%m-%dT%H:%M"))
    assert exp_dict["last_updated"].startswith(today.strftime("%Y-%m-%dT%H:%M"))
    assert exp_dict["dependencies"] == []
    assert exp_dict["short_slug"] == "my-experiment"
    assert exp_dict["slug"].startswith(f"my-experiment-{today.strftime('%Y%m%d%H%M')}")
    assert exp_dict["tests"] == [
        {
            "name": "My test",
            "description": None,
            "metrics": {"subpop": 0.7},
            "parameters": {"param": "value"},
        }
    ]
    assert exp_dict["artifacts"] == [
        {
            "name": "features",
            "fname": f"features-{today.strftime('%Y%m%d%H%M%S')}.json",
            "handler": "json",
            "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
            "python_version": ".".join(str(i) for i in sys.version_info[:2]),
            "version": 0,
        }
    ]
    assert exp_dict["tags"] == ["success"]


@pytest.mark.parametrize("parametrized", [True, False])
def test_prefect_project(parametrized, tmp_path):
    """Test lazyscribe project integration with projects."""
    location = tmp_path / "my-project"
    location.mkdir()
    project_location = location / "project.json"

    if parametrized:
        init_project = LazyProject(author="root")
    else:
        init_project = LazyProject(fpath=project_location, author="root")
    with Flow(name="Create project") as flow:
        if parametrized:
            param = Parameter(name="fpath", default=project_location)
            project = init_project(fpath=param)
        else:
            project = init_project()

        with project.log(name="My experiment") as experiment:
            experiment.log_metric("name", 0.5)
            experiment.log_parameter("param", "value")
            with experiment.log_test(name="My test") as test:
                test.log_parameter("param", "value")
                test.log_metric("subpop", 0.7)

        exp_data, test_data = project.to_tabular()
        project.save()

    assert {tsk.name for tsk in flow.downstream_tasks(project)} == {
        "My experiment",
        "Append experiment",
        "Create tabular data",
        "Save project",
    }
    assert {tsk.name for tsk in flow.downstream_tasks(experiment)} == {
        "Log experiment metric",
        "Log parameter",
        "Append test",
        "Append experiment",
    }
    assert {
        tsk.name
        for tsk in flow.downstream_tasks(flow.get_tasks(name="Append experiment")[0])
    } == {"Create tabular data", "Save project"}
    assert {
        tsk.name
        for tsk in flow.downstream_tasks(
            flow.get_tasks(name="Log experiment metric")[0]
        )
    } == {
        "Append experiment",
    }
    assert {
        tsk.name
        for tsk in flow.downstream_tasks(flow.get_tasks(name="Log parameter")[0])
    } == {"Append experiment"}
    assert {tsk.name for tsk in flow.downstream_tasks(test)} == {
        "Log test metric",
        "Log test parameter",
        "Append test",
    }
    assert {
        tsk.name
        for tsk in flow.downstream_tasks(flow.get_tasks(name="Log test metric")[0])
    } == {"Append test"}

    output = flow.run()
    proj_list = list(output.result[project].result)
    today = datetime.now()

    assert output.is_successful()
    assert len(proj_list) == 1
    assert proj_list[0]["name"] == "My experiment"
    assert proj_list[0]["author"] == "root"
    assert proj_list[0]["last_updated_by"] == "root"
    assert proj_list[0]["metrics"] == {"name": 0.5}
    assert proj_list[0]["parameters"] == {"param": "value"}
    assert proj_list[0]["created_at"].startswith(today.strftime("%Y-%m-%dT%H:%M"))
    assert proj_list[0]["last_updated"].startswith(today.strftime("%Y-%m-%dT%H:%M"))
    assert proj_list[0]["dependencies"] == []
    assert proj_list[0]["short_slug"] == "my-experiment"
    assert proj_list[0]["slug"].startswith(
        f"my-experiment-{today.strftime('%Y%m%d%H%M')}"
    )
    assert proj_list[0]["tests"] == [
        {
            "name": "My test",
            "description": None,
            "metrics": {"subpop": 0.7},
            "parameters": {"param": "value"},
        }
    ]

    assert output.result[project].result.to_tabular() == (
        output.result[exp_data].result,
        output.result[test_data].result,
    )
    assert project_location.exists()


def test_prefect_project_merge():
    """Test merging projects with prefect."""
    init_base = LazyProject(fpath=DATA_DIR / "project.json", mode="r")
    init_new = LazyProject(fpath=DATA_DIR / "merge_append.json", mode="r")

    with Flow(name="Merge projects") as flow:
        base = init_base()
        new = init_new()
        updated = base.merge(new)

    output = flow.run()
    assert output.is_successful()

    assert list(output.result[updated].result) == [
        {
            "name": "My experiment",
            "author": "root",
            "last_updated_by": "root",
            "metrics": {"name": 0.5},
            "parameters": {},
            "created_at": "2022-01-01T09:30:00",
            "last_updated": "2022-01-01T09:30:00",
            "dependencies": [],
            "short_slug": "my-experiment",
            "slug": "my-experiment-20220101093000",
            "artifacts": [],
            "tests": [
                {
                    "name": "My test",
                    "description": None,
                    "metrics": {"name-subpop": 0.3},
                    "parameters": {"param": "value"},
                }
            ],
            "tags": [],
        },
        {
            "name": "My second experiment",
            "author": "root",
            "last_updated_by": "root",
            "metrics": {},
            "parameters": {"features": ["col1", "col2"]},
            "created_at": "2022-01-01T10:30:00",
            "last_updated": "2022-01-01T10:30:00",
            "dependencies": [],
            "short_slug": "my-second-experiment",
            "slug": "my-second-experiment-20220101103000",
            "artifacts": [],
            "tests": [],
            "tags": [],
        },
    ]
