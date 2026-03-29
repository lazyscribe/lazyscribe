"""Test concurrency support for Lazyscribe."""

import json
import tempfile
import zoneinfo
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import time_machine
from slugify import slugify

from lazyscribe import Project


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

        # Create a function that logs experiments
        def _logging_function(
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

        project = Project(self.dir / "threaded-repository.json", mode="w")
        with ThreadPoolExecutor(max_workers=4) as tpe:
            futures = []
            for arg in self.params:
                futures.append(tpe.submit(_logging_function, project, *arg))
            for f in futures:
                f.result()

        project.save()

        assert Path(self.dir / "threaded-repository.json").is_file()

        with open(self.dir / "repository.json") as infile:
            ref_project_ = json.load(infile)
        with open(self.dir / "threaded-repository.json") as infile:
            threaded_project_ = json.load(infile)

        assert threaded_project_ == ref_project_

    @classmethod
    def teardown_class(cls):
        """Teardown the class."""
        cls.location.cleanup()
