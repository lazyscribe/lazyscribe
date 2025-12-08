"""
Create deployment releases for your repository
==============================================

In this tutorial we will demonstrate how you can create a release of related artifact/version
combinations from your :py:class:`lazyscribe.repository.Repository` instances.

The goal of a release is to allow users to easily "time-travel" safely to points in time that
have semantic meaning to the project/deployment as a whole. First, let's create our deployment.

.. note::
    In this tutorial, you'll see us use ``time-machine`` to specify datetimes. We are
    doing this because the tutorial code logs multiple versions of the same artifact
    within 1 second of each other, which can cause unexpected behaviour when calling
    :py:meth:`lazyscribe.repository.Repository.save`.
"""

# %%

import tempfile
import zoneinfo
from datetime import datetime
from pathlib import Path

import time_machine
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

import lazyscribe.release as lzr
from lazyscribe import Repository

tmpdir = Path(tempfile.mkdtemp())
repository = Repository(tmpdir / "repository.json", mode="w+")

# %%
# Let's fit and log our model to the repository.

with time_machine.travel(
    datetime(2025, 12, 8, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
):
    X, y = make_classification(n_samples=1000, n_features=10)
    model = SVC(kernel="linear")
    model.fit(X, y)

    repository.log_artifact("model", model, handler="pickle")
    repository.log_artifact("features", list(range(10)), handler="json", indent=4)

    repository.save()

# %%
# Now, let's read in our saved repository and create a release based on our artifacts:

saved_ = Repository(tmpdir / "repository.json", mode="r")
release = lzr.create_release(saved_, "v0.1.0")
print(release)

# %%
# This object contains the latest artifact and version combination available in our repository.
# Each artifact name only exists *once* in this data structure.
#
# Now, we can persist the release information to a JSON file for easy reference later.

with open(tmpdir / "releases.json", "w") as outfile:
    lzr.dump([release], outfile, indent=4)

# %%
# Now, let's use this functionality in action. First, we need to fit and log a new model:

with time_machine.travel(
    datetime(2025, 12, 25, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
):
    modelv1 = LogisticRegression()
    modelv1.fit(X, y)

    repository.log_artifact("model", modelv1, handler="pickle")

repository.save()

# %%
# Now, let's read in the release and filter our repository to ensure that the end user
# gets the version of the model they intend.

saved_ = Repository(tmpdir / "repository.json", mode="r")
with open(tmpdir / "releases.json") as infile:
    releases = lzr.load(infile)

my_release = lzr.find_release(releases, "v0.1.0")
filtered_ = repository.filter(my_release.artifacts)

# %%
# ``filtered_`` is a repository that only contains the artifact/version combinations that appear
# in the release. What does this mean? We can time travel without having to know the exact version
# of the artifact we want to load. All we need to know is the release:

first_model_ = filtered_.load_artifact(name="model")
print(first_model_)

# %%
# This functionality is designed for complex, long-running deployment environments.
#
# Now, one common usage pattern we see is using a project (through ``pyproject.toml``) to manage
# a group of lazyscribe repository objects. Let's synchronize our project version with our repositories:

pyproject_data_ = f"""
[project]
name = "my-complex-deployment"
version = "0.2.0"

[tool.lazyscribe]
repositories = [
    "{tmpdir / "repository.json"}
]
"""

lzr.release_from_toml(pyproject_data_)

# %%
# This function will create a release for our listed repository with version 0.2.0:

with open(tmpdir / "releases.json") as infile:
    releases = lzr.load(infile)

print(releases)
