"""
Creating a basic project
========================

In this tutorial, we will demonstrate how you can create a project and log a single
experiment.
"""

import json

import pandas as pd
from sklearn.datasets import make_classification
from sklearn.svm import SVC

from lazyscribe import Project

# %%
# First, let's create some toy data for the experiment.

X, y = make_classification(n_samples=1000, n_features=10)

# %%
# Next, create the project and run the model fit

project = Project(fpath="project.json", author="The Best")
with project.log(name="Base performance") as exp:
    model = SVC(kernel="linear")
    model.fit(X, y)
    exp.log_metric("score", model.score(X, y))
    exp.log_parameter("features", list(range(10)))

# %%
# Finally, let's print and view the experiment data.

print(json.dumps(list(project), indent=4, sort_keys=True))

# %%
# You can also represent the project in a table:

experiments, tests = project.to_tabular()

df = pd.DataFrame(experiments)
df.columns = pd.MultiIndex.from_tuples(df.columns)
df.head()

# %%
# Then, you can call :py:meth:`lazyscribe.Project.save` to save the output JSON.
