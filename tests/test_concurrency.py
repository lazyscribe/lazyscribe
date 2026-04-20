"""Test concurrency support for Lazyscribe."""

import json
import tempfile
import zoneinfo
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timedelta
from operator import itemgetter
from pathlib import Path

import time_machine
from slugify import slugify

from lazyscribe import Experiment, Project


def _project_logging_function(
    project: Project,
    name: str,
    metric: float,
    ts: datetime,
):
    """Create an experiment."""
    with project.log(name) as exp:
        exp.log_metric("name", metric)
        # Manually setting timestamp-related fields because time-machine
        # is not thread-safe
        exp.created_at = ts.replace(tzinfo=None)
        exp.last_updated = ts.replace(tzinfo=None)
        exp.slug = f"{slugify(name)}-{ts.strftime('%Y%m%d%H%M%S')}"

    return project


class TestProjectConcurrency:
    """Test logging experiments in multiple threads.

    Testing design largely built based on the Free Threading guide:
    https://py-free-threading.github.io/testing/
    """

    @classmethod
    def setup_class(cls):
        """Create a reference project for comparison."""
        cls.location = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.location.name)

        # Create standard parameters for experiments
        cls.params = [
            (
                f"{idx} Experiment",
                idx / 100,
                datetime(2026, 3, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC"))
                + timedelta(hours=idx),
            )
            for idx in range(1, 101)
        ]

        # Create a few experiments
        project = Project(cls.dir / "repository.json", mode="w")
        for param in cls.params:
            with (
                time_machine.travel(param[2], tick=False),
                project.log(name=param[0]) as exp,
            ):
                exp.log_metric("name", param[1])

        project.save()

    def test_multithreaded_logging(self):
        """Test logging experiments in multiple threads."""
        project = Project(self.dir / "threaded-repository.json", mode="w")
        with ThreadPoolExecutor(max_workers=4) as tpe:
            futures = []
            for arg in self.params:
                futures.append(tpe.submit(_project_logging_function, project, *arg))
            for f in futures:
                _ = f.result()

        project.save()

        assert Path(self.dir / "threaded-repository.json").is_file()

        with open(self.dir / "repository.json") as infile:
            ref_project_ = json.load(infile)
        with open(self.dir / "threaded-repository.json") as infile:
            threaded_project_ = json.load(infile)

        assert threaded_project_ == ref_project_

    def test_multiprocessing_logging(self):
        """Test logging experiments in multiple processes."""
        project = Project(self.dir / "multiprocess-repository.json", mode="w")
        with ProcessPoolExecutor(max_workers=4) as ppe:
            futures = []
            for arg in self.params:
                futures.append(ppe.submit(_project_logging_function, project, *arg))
            projects_ = [f.result() for f in futures]

        process_project_ = project.merge(*projects_)
        process_project_.save()

        with open(self.dir / "repository.json") as infile:
            ref_project_ = json.load(infile)
        with open(self.dir / "multiprocess-repository.json") as infile:
            out_project_ = json.load(infile)

        assert out_project_ == ref_project_

    @classmethod
    def teardown_class(cls):
        """Teardown the class."""
        cls.location.cleanup()


class TestExperimentConcurrency:
    """Test logging tests to a single experiment in parallel."""

    @classmethod
    def setup_class(cls):
        """Create a reference project for comparison."""
        cls.location = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.location.name)

        # Create a single experiment with multiple parameters, metrics,
        # and tests.
        cls.params = [
            {
                "name": f"test-{idx}",
                "metrics": (f"metric-{idx}", idx / 100),
                "parameters": (f"iter-{idx}", idx),
            }
            for idx in range(1, 101)
        ]
        project = Project(cls.dir / "repository.json", mode="w")
        with (
            time_machine.travel(
                datetime(2026, 3, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")),
                tick=False,
            ),
            project.log(name="My experiment") as exp,
        ):
            for arg in cls.params:
                with exp.log_test(arg["name"]) as test:
                    test.log_metric(arg["metrics"][0], arg["metrics"][1])
                    test.log_parameter(arg["parameters"][0], arg["parameters"][1])

        project.save()

    def test_multithreaded_logging(self):
        """Test logging tests in multiple threads."""

        # Create a function that logs tests to a single experiment
        def _logging_function(experiment: Experiment, payload: dict, ts: datetime):
            """Modify an experiment."""
            with experiment.log_test(payload["name"]) as test:
                test.log_metric(payload["metrics"][0], payload["metrics"][1])
                test.log_parameter(payload["parameters"][0], payload["parameters"][1])

        project = Project(self.dir / "threaded-repository.json", mode="w")
        ts = datetime(2026, 3, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC"))
        with (
            time_machine.travel(ts, tick=False),
            ThreadPoolExecutor(max_workers=4) as tpe,
            project.log(name="My experiment") as exp,
        ):
            futures = []
            for arg in self.params:
                futures.append(tpe.submit(_logging_function, exp, arg, ts))
            for f in futures:
                f.result()

        project.save()

        assert Path(self.dir / "threaded-repository.json").is_file()

        with open(self.dir / "repository.json") as infile:
            ref_project_ = json.load(infile)
        with open(self.dir / "threaded-repository.json") as infile:
            threaded_project_ = json.load(infile)

        # When checking the equality of tests, we don't care about order
        threaded_tests_ = sorted(
            threaded_project_[0].pop("tests"),
            key=itemgetter("name"),
        )
        ref_tests_ = sorted(ref_project_[0].pop("tests"), key=itemgetter("name"))

        assert threaded_tests_ == ref_tests_
        assert threaded_project_ == ref_project_

    @classmethod
    def teardown_class(cls):
        """Teardown the class."""
        cls.location.cleanup()
