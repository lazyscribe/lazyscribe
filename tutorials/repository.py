"""
Creating a basic repository for your artifacts
==============================================

In this tutorial, we will demonstrate how you can create a repository and log artifacts.

A repository is an organized structure that stores and versions your artifacts.
It makes it easy to retrieve older versions of artifacts, log new ones or time travel.
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

from lazyscribe import Repository

# %%
# First, we're going to train version 0 of our model that we want to deploy.

X, y = make_classification(n_samples=1000, n_features=10)
model = SVC(kernel="linear")
model.fit(X, y)

# %%
# Next, we initialize our repository. In this tutorial we will use a temporary
# path, but you can use a :doc:`local path or external filesystem <../how-to/external-fs>`.

tmpdir = Path(tempfile.mkdtemp())
repository = Repository(tmpdir / "repository.json", mode="w+")

# %%
# Let's log version 0 of our model to our repository alongside the list of input features.
# Remember to save! Nothing is actually written to file until you save.
#
# .. note::
#
#     In this tutorial, you'll see us use ``time-machine`` to specify datetimes. We are
#     doing this because the tutorial code logs multiple versions of the same artifact
#     within 1 second of each other, which can cause unexpected behaviour when calling
#     :py:meth:`lazyscribe.repository.Repository.save`.

with time_machine.travel(
    datetime(2025, 10, 31, 17, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
):
    repository.log_artifact("model", model, handler="pickle")
    repository.log_artifact("features", list(range(10)), handler="json", indent=4)
    repository.save()

# %%
# Let's simulate a deployment environment by initializing a read-only instance of
# :py:class:`lazyscribe.repository.Repository`.

repository_read = Repository(tmpdir / "repository.json", mode="r")
repository_read.load_artifact("model")

# %%
# Say we have trained a newer, better version of our model. We can log it as
# version 1 of our model artifact. Remember to save!

with time_machine.travel(
    datetime(2025, 11, 1, 17, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
):
    modelv1 = LogisticRegression()
    modelv1.fit(X[:, 0:9], y)
    repository.log_artifact("model", modelv1, handler="pickle")
    repository.log_artifact("features", list(range(9)), handler="json", indent=4)
    repository.save()

# %%
# :py:meth:`lazyscribe.repository.Repository.load_artifact` will, by default, load
# the latest version of our model.

repository_read = Repository(tmpdir / "repository.json", mode="r")
repository_read.load_artifact("model")

# %%
# We can still time travel back to version 0 of our model artifact by specifying
# either the integer version, the datetime it was created, or a string version of
# the datetime.

repository_read.load_artifact("model", version=0)

# %%
# We can also observe the differences between our features list using ``difflib``.
# Here, we are comparing version 0 of the ``features`` artifact against the latest
# version.

print(repository_read.get_version_diff("features", version=0))
