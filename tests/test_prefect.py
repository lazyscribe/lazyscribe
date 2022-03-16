"""Test the prefect integration."""

from datetime import datetime
from pathlib import Path

from prefect import Flow

from lazyscribe.prefect import LazyExperiment, LazyProject


def test_prefect_experiment():
    """Test creating an experiment and logging basic parameters."""
    init_experiment = LazyExperiment()
    with Flow(name="Create experiment") as flow:
        experiment = init_experiment(
            project=Path("project.json"), name="My experiment", author="root"
        )
        experiment.log_metric("name", 0.5)
        experiment.log_parameter("param", "value")
        with experiment.log_test(name="My test") as test:
            test.log_metric("subpop", 0.7)

    assert {tsk.name for tsk in flow.downstream_tasks(experiment)} == {
        "Log experiment metric", "Log parameter", "Append test"
    }
    assert flow.downstream_tasks(flow.get_tasks(name="Log experiment metric")[0]) == set()
    assert flow.downstream_tasks(flow.get_tasks(name="Log parameter")[0]) == set()
    assert {tsk.name for tsk in flow.downstream_tasks(test)} == {
        "Log test metric", "Append test"
    }
    assert {
        tsk.name for tsk in flow.downstream_tasks(flow.get_tasks(name="Log test metric")[0])
    } == {"Append test"}

    output = flow.run()
    today = datetime.now()

    assert output.is_successful()
    assert output.result[experiment].result.to_dict() == {
        "name": "My experiment",
        "author": "root",
        "last_updated_by": "root",
        "metrics": {"name": 0.5},
        "parameters": {"param": "value"},
        "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "last_updated": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "dependencies": [],
        "short_slug": "my-experiment",
        "slug": f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}",
        "tests": [
            {
                "name": "My test",
                "description": None,
                "metrics": {"subpop": 0.7}
            }
        ]
    }


def test_prefect_project(tmpdir):
    """Test lazyscribe project integration with projects."""
    location = tmpdir.mkdir("my-project")
    project_location = Path(str(location)) / "project.json"

    init_project = LazyProject(fpath=project_location, author="root")
    with Flow(name="Create project") as flow:
        project = init_project()
        with project.log(name="My experiment") as experiment:
            experiment.log_metric("name", 0.5)
            experiment.log_parameter("param", "value")
            with experiment.log_test(name="My test") as test:
                test.log_metric("subpop", 0.7)

        exp_data, test_data = project.to_tabular()
        project.save()

    assert {tsk.name for tsk in flow.downstream_tasks(project)} == {
        "My experiment", "Append experiment", "Create tabular data", "Save project"
    }
    assert {tsk.name for tsk in flow.downstream_tasks(experiment)} == {
        "Log experiment metric", "Log parameter", "Append test", "Append experiment"
    }
    assert {tsk.name for tsk in flow.downstream_tasks(flow.get_tasks(name="Append experiment")[0])} == {
        "Create tabular data", "Save project"
    }
    assert {tsk.name for tsk in flow.downstream_tasks(flow.get_tasks(name="Log experiment metric")[0])} == {
        "Append experiment",
    }
    assert {tsk.name for tsk in flow.downstream_tasks(flow.get_tasks(name="Log parameter")[0])} == {
        "Append experiment"
    }
    assert {tsk.name for tsk in flow.downstream_tasks(test)} == {
        "Log test metric", "Append test"
    }
    assert {tsk.name for tsk in flow.downstream_tasks(flow.get_tasks(name="Log test metric")[0])} == {
        "Append test"
    }

    output = flow.run()
    today = datetime.now()

    assert output.is_successful()
    assert list(output.result[project].result) == [
        {
            "name": "My experiment",
            "author": "root",
            "last_updated_by": "root",
            "metrics": {"name": 0.5},
            "parameters": {"param": "value"},
            "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
            "last_updated": today.strftime("%Y-%m-%dT%H:%M:%S"),
            "dependencies": [],
            "short_slug": "my-experiment",
            "slug": f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}",
            "tests": [
                {
                    "name": "My test",
                    "description": None,
                    "metrics": {"subpop": 0.7}
                }
            ]
        }
    ]
    assert output.result[project].result.to_tabular() == (
        output.result[exp_data].result, output.result[test_data].result
    )
    assert project_location.exists()
