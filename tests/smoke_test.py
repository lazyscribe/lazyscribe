"""Check that basic features work.

Used in our publishing pipeline.
"""

import json
import tempfile
from pathlib import Path

from lazyscribe import Project, Repository

with tempfile.TemporaryDirectory() as tmpdir:
    # Create a project
    project = Project(fpath=Path(tmpdir) / "project.json", mode="w")
    with project.log(name="Basic experiment") as exp:
        exp.log_metric("performance", 0.75)
        exp.log_parameter("features", [0, 1, 2, 3, 4])
        exp.log_artifact(
            name="feature-names", value=["a", "b", "c", "d", "e"], handler="json"
        )

    project.save()

    with open(Path(tmpdir) / "project.json") as infile:
        project_data_ = json.load(infile)

    assert len(project_data_) == 1

    # Promote the artifact to the repository
    repo = Repository(Path(tmpdir) / "repository.json", mode="w")
    exp = project["basic-experiment"]
    exp.promote_artifact(repo, "feature-names")

    art = repo.load_artifact(name="feature-names")

    assert art == ["a", "b", "c", "d", "e"]
