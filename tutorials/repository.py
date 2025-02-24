"""
Creating a basic repository for your artifacts
==============================================

In this tutorial, we will demonstrate how you can create a repository and log artifacts.

A repository is an organized structure that stores and versions your artifacts.
It makes it easy to retrieve older versions of artifacts, log new ones or time travel.
"""

# %%
import tempfile
from pathlib import Path

from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

from lazyscribe import Repository

# %%
# First, we're going to train version 0 of our model that we want to deploy

X, y = make_classification(n_samples=1000, n_features=10)
model = SVC(kernel="linear")
model.fit(X, y)

# %%
# Next, we initialize our repository. Here, we're using a temporary path, but you can use a local path or an external filesystem URI as well.
tmpdir = Path(tempfile.mkdtemp())
repository = Repository(tmpdir / "repository.json", mode="w")

# %%
# Let's log version 0 of our model to our repository. Remember to save! Nothing is actually written to file until you save.

repository.log_artifact("model", model, handler="joblib")
repository.save()

# %%
# If we want to retrieve our artifact, we need to initialize a read-only instance of ``Repository``.

repository_read = Repository(tmpdir / "repository.json", mode="r")
repository_read.load_artifact("model")

# %%
# Say we have trained a newer, better version of our model. We can log it as version 1 of our model artifact. Remember to save!

modelv1 = LogisticRegression()
modelv1.fit(X, y)
repository.log_artifact("model", modelv1, handler="joblib")
repository.save()

# %%
# Now, if we load our model artifact, it defaults to the most recent.
repository_read = Repository(tmpdir / "repository.json", mode="r")
repository_read.load_artifact("model")
# %%
# We can still time travel back to version 0 of our model artifact by specifying either the integer version, the datetime it was created, or a string version of the datetime.

repository_read.load_artifact("model", version=0)
