"""
Workflow integration with Prefect
=================================

In this tutorial, we will demonstrate how you can use ``lazyscribe`` with ``prefect``.
"""

import json

import numpy as np
from prefect import Flow, task
from sklearn.datasets import make_classification
from sklearn.svm import SVC

from lazyscribe.prefect import LazyProject

# %%
# First, let's make some tasks to generate fake data, train an estimator, and score the model.


@task(name="Generate data", nout=2)
def generate_data(
    n_samples: int = 1000, n_features: int = 10
) -> tuple[np.ndarray, np.ndarray]:
    """Generate classification data.

    Parameters
    ----------
    n_samples : int, optional (default 1000)
        The number of samples to generate.
    n_features : int, optional (default 10)
        The number of features in the classification dataset.

    Returns
    -------
    np.ndarray
        The feature space.
    np.ndarray
        The response vector.
    """
    return make_classification(n_samples=1000, n_features=10)


@task(name="Train SVM")
def fit_model(X: np.ndarray, y: np.ndarray) -> SVC:
    """Train a SVM.

    Parameters
    ----------
    X : np.ndarray
        The feature space.
    y : np.ndarray
        The response vector.

    Returns
    -------
    SVC
        Fitted ``SVC`` object.
    """
    return SVC(kernel="linear").fit(X, y)


@task(name="Score model")
def score_model(estimator: SVC, X: np.ndarray, y: np.ndarray) -> float:
    """Score a model.

    Parameters
    ----------
    estimator : SVC
        Fitted estimator.
    X : np.ndarray
        Feature space.
    y : np.ndarray
        Response vector.

    Returns
    -------
    float
        The score.
    """
    return estimator.score(X, y)


# %%
# Next, let's create a flow that fits the model and logs output:

init_project = LazyProject(fpath="project.json", author="The Best")
with Flow(name="Fit estimator") as flow:
    project = init_project()
    with project.log(name="Base performance") as exp:
        X, y = generate_data()
        estimator = fit_model(X, y)
        score = score_model(estimator, X, y)
        exp.log_metric("score", score)

# %%
# Let's run the flow.

output = flow.run()
assert output.is_successful()

# %%
# We can print the experiment to look at the data.

print(json.dumps(list(output.result[project].result), indent=4, sort_keys=True))
