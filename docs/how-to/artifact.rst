Save and examine experiment artifacts
=====================================

In this guide, we will walk through how you can save artifacts associated
with your experiment.

Persistence
-----------

Every experiment has a ``path`` attribute, with the :py:class:`pathlib.Path`
to a unique folder based on experiment slug:

.. code-block:: python

    from lazyscribe import Project

    project = Project(fpath="project.json", mode="w")
    with project.log("My experiment") as exp:
        exp.path

This will return ``Path("./my-experiment-YYYYMMDDHHMMSS")``, where the datetime
corresponds to the ``created_at`` attribute.

.. important::

  Unless you log an artifact, this directory will not be created automatically.

To associate an artifact with your experiment, use :py:meth:`lazyscribe.Experiment.log_artifact`.
Serialization is delegated to a subclass of :py:class:`lazyscribe.artifacts.Artifact`.

.. code-block:: python
    :caption: Persisting a ``scikit-learn`` estimator with ``joblib``.
    :emphasize-lines: 8-9

    from lazyscribe import Project
    from sklearn.svm import SVC

    project = Project(fpath="project.json", mode="w")
    with project.log("My experiment") as exp:
        X, y = ...
        model = SVC()
        model.fit(X, y)
        exp.log_artifact(name="estimator", value=model, handler="joblib")

In the case of code failures, we want to minimize the chance that you need to clean up orphaned
experiment data. For this reason, artifacts are *not persisted to the filesystem* when you call
:py:meth:`lazyscribe.Experiment.log_artifact`. Artifacts are **only** saved when you
call :py:meth:`lazyscribe.Project.save`.

Below, we have included a list of currently supported artifact handlers and their aliases:

.. list-table:: Builtin artifact handlers
    :header-rows: 1

    * - Class
      - Alias
      - Description
      - Additional requirements
    * - :py:class:`lazyscribe.artifacts.JSONArtifact`
      - json
      - Artifacts written using :py:meth:`json.dump` and read using :py:meth:`json.load`
      - N/A
    * - :py:class:`lazyscribe.artifacts.JoblibArtifact`
      - joblib
      - Artifacts written using :py:meth:`joblib.dump` and read using :py:meth:`joblib.load`
      - ``joblib``

Loading and validation
----------------------

To load an artifact, use :py:meth:`lazyscribe.Experiment.load_artifact`.

.. code-block:: python
    :emphasize-lines: 5

    from lazyscribe import Project

    project = Project("project.json", mode="r")
    exp = project["my-experiment"]
    model = exp.load_artifact(name="estimator")

When an artifact is persisted to the filesystem, the handler may save environment
parameters to use for validation when attempting to load the artifact into python.
For example, when persisting a ``scikit-learn`` model object with the :py:class:`lazyscribe.artifacts.JoblibArtifact`, it will include the ``scikit-learn``
and ``joblib`` versions in the artifact metadata. If the metadata doesn't match with a handler constructed
in the current runtime environment, ``lazyscribe`` will raise an error. You can disable validation using
``validate=False``:

.. code-block:: python

    model = exp.load_artifact(name="estimator", validate=False)
