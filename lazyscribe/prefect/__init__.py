"""Import the tasks."""

from lazyscribe.prefect.experiment import (
    LazyExperiment,
    append_test,
    log_experiment_metric,
    log_parameter,
)
from lazyscribe.prefect.project import (
    LazyProject,
    append_experiment,
    merge_projects,
    save_project,
)
from lazyscribe.prefect.test import LazyTest, log_test_metric

__all__: list[str] = [
    "LazyExperiment",
    "LazyProject",
    "LazyTest",
    "append_experiment",
    "append_test",
    "log_experiment_metric",
    "log_parameter",
    "log_test_metric",
    "merge_projects",
    "save_project",
]
