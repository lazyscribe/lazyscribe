"""
Logging non-global metrics and artifacts with tests
====================================================

In this tutorial, we will demonstrate how you can use
:py:class:`lazyscribe.test.Test` objects to log metrics, parameters, and artifacts
for specific sub-populations of your experiment data.

A common pattern in ML development is to evaluate a model on the overall dataset
*and* on specific data slices (e.g. by demographic group, data source, or class).
Attaching these per-slice results directly to the experiment — rather than keeping
them in separate files — makes it easier to compare slices across experiments and
to reproduce past evaluations.
"""

# %%

import json
import tempfile
from pathlib import Path

from sklearn.datasets import make_classification
from sklearn.svm import SVC

from lazyscribe import Project

# %%
# First, create some toy data and split off a "subpopulation" (the last 200 samples).

X, y = make_classification(n_samples=1000, n_features=10, random_state=0)
X_sub, y_sub = X[800:], y[800:]

# %%
# Next, initialise the project and run the experiment. We use :py:meth:`lazyscribe.experiment.Experiment.log_test`
# as a context manager to log the sub-population evaluation.
#
# Inside the context, we can call the same :py:meth:`~lazyscribe.test.Test.log_metric`
# and :py:meth:`~lazyscribe.test.Test.log_parameter` methods as on a regular experiment,
# as well as the new :py:meth:`~lazyscribe.test.Test.log_artifact` method.

tmpdir = Path(tempfile.mkdtemp())
project = Project(fpath=tmpdir / "project.json", mode="w")

with project.log(name="base-performance") as exp:
    model = SVC(kernel="linear", random_state=0)
    model.fit(X, y)
    exp.log_metric("score", model.score(X, y))

    with exp.log_test(name="subpopulation-a") as test:
        sub_score = model.score(X_sub, y_sub)
        predictions = model.predict(X_sub).tolist()

        test.log_metric("score", sub_score)
        test.log_parameter("n_samples", len(y_sub))

        # Persist the predictions list as a JSON artifact.
        test.log_artifact(name="predictions", value=predictions, handler="json")

# %%
# Artifacts are **not** written to disk at call time. Call :py:meth:`lazyscribe.Project.save`
# to persist both the project JSON and any pending artifact files.

project.save()

# %%
# Let's verify the test was captured by printing its data.

exp_data = project["base-performance"]
test_data = exp_data.tests[0]
print(json.dumps(test_data.to_dict(), indent=4, default=str))

# %%
# To reload the test artifact in a later session, open the project in read mode and call
# :py:meth:`lazyscribe.test.Test.load_artifact` on the test.

project_read = Project(fpath=tmpdir / "project.json", mode="r")
exp_read = project_read["base-performance"]
test_read = exp_read.tests[0]
loaded_predictions = test_read.load_artifact("predictions")

print(loaded_predictions)
