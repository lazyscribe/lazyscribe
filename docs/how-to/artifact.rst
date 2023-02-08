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

    project = Project()
    with project.log("My experiment") as exp:
        exp.path

This will return ``Path("./my-experiment-YYYYMMDDHHMMSS")``, where the datetime
corresponds to the ``created_at`` attribute. To save an artifact to this directory,
use :py:meth:`lazyscribe.Experiment.log_artifact`. Serialization is delegated to
a subclass of :py:class:`lazyscribe.artifacts.Artifact`. For example, suppose
you have a ``scikit-learn`` estimator:

.. code-block:: python
    :emphasize-lines: 9

    from lazyscribe import Project
    from sklearn.svm import SVC

    project = Project()
    with project.log("My experiment") as exp:
        X, y = ...
        model = SVC()
        model.fit(X, y)
        exp.log_artifact(fname="estimator.joblib", value=model, handler="scikit-learn")

In this case, the estimator will be persisted using ``joblib``. Below, we have included
a list of currently supported artifact handlers and their aliases:

.. list-table:: Builtin artifact handlers
    :header-rows: 1

    * - Class
      - Alias
      - Description
    * - :py:class:`lazyscribe.artifacts.JSONArtifact`
      - json
      - Artifacts written using :py:meth:`json.dump` and read using :py:meth:`json.load`
    * - :py:class:`lazyscribe.artifacts.SklearnArtifact`
      - scikit-learn
      - Artifacts written using :py:meth:`joblib.dump` and read using :py:meth:`joblib.load`

Loading and validation
----------------------

To load an artifact, use :py:meth:`lazyscribe.Experiment.load_artifact`. The name of the artifact
is the stem of the filename (e.g. for the above ``estimator.joblib``, the name will be ``estimator``).

.. code-block:: python
    :emphasize-lines: 5

    from lazyscribe import Project

    project = Project("project.json", mode="r")
    exp = project["my-experiment"]
    model = exp.load_artifact(name="estimator")

When an artifact is persisted to the filesystem, the handler may save environment
parameters to use for validation when attempting to load the artifact into python.
For example, :py:class:`lazyscribe.artifacts.SklearnArtifact` will include the ``scikit-learn``
and ``joblib`` versions in the artifact metadata. If the metadata doesn't match with a handler constructed
in the current runtime environment, an error will be raised. However, you can disable validation using
``validate=False``:

.. code-block:: python

    model = exp.load_artifact(name="estimator", validate=False)
