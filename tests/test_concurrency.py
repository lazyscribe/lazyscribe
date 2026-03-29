"""Test concurrency support for Lazyscribe."""

import json
import tempfile
import threading
import zoneinfo
from datetime import datetime
from pathlib import Path

import time_machine
from slugify import slugify

from lazyscribe import Project


class TestProjectConcurrency:
    """Test logging experiments in multiple threads."""

    @classmethod
    def setup_class(cls):
        """Create a reference project for comparison."""
        cls.location = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.location.name)

        # Create a few experiments
        project = Project(cls.dir / "repository.json", mode="w")
        with (
            time_machine.travel(
                datetime(2026, 3, 15, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")),
                tick=False,
            ),
            project.log(name="First experiment") as exp,
        ):
            exp.log_metric("name", 0.5)
        with (
            time_machine.travel(
                datetime(2026, 3, 20, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")),
                tick=False,
            ),
            project.log(name="Second experiment") as exp,
        ):
            exp.log_metric("name", 0.75)
        with (
            time_machine.travel(
                datetime(2026, 3, 25, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")),
                tick=False,
            ),
            project.log(name="Third experiment") as exp,
        ):
            exp.log_metric("name", 1.0)

        project.save()

    def test_multithreaded_logging(self):
        """Test logging experiments in multiple threads."""

        # Create a function that logs experiments
        def _logging_function(project: Project, name: str, metric: float, ts: datetime):
            """Create an experiment."""
            with project.log(name) as exp:
                exp.log_metric("name", metric)
                # Manually setting timestamp-related fields because time-machine
                # is not thread-safe
                exp.created_at = ts
                exp.last_updated = ts
                exp.slug = f"{slugify(name)}-{ts.strftime('%Y%m%d%H%M%S')}"

        project = Project(self.dir / "threaded-repository.json", mode="w")
        threads = [
            threading.Thread(target=_logging_function, args=param)
            for param in [
                (
                    project,
                    "First experiment",
                    0.5,
                    datetime(2026, 3, 15, 0, 0, 0),
                ),
                (
                    project,
                    "Second experiment",
                    0.75,
                    datetime(2026, 3, 20, 0, 0, 0),
                ),
                (
                    project,
                    "Third experiment",
                    1.0,
                    datetime(2026, 3, 25, 0, 0, 0),
                ),
            ]
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

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
