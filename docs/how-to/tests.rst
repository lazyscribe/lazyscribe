Log non-global metrics
======================

Sometimes, it's helpful to log non-global metrics to an experimenent. To do so, create a
:py:class:`lazyscribe.test.Test` using :py:meth:`lazyscribe.experiment.Experiment.log_test`:

.. code-block:: python

    from lazyscribe import Project

    project = Project(fpath="project.json", mode="w")

    with project.log(name="My experiment") as exp:
        with exp.log_test(name="My test", description="Demo test") as test:
            test.log_metric("metric", 0.3)
            test.log_parameter("param", "value")

The test's parameter has been also stored here.

The :py:meth:`lazyscribe.experiment.Experiment.log_test` context handler creates a :py:class:`lazyscribe.test.Test` object and
logs it back to the experiment when the handler exits. If you want to avoid using the context
handler, instantiate your own test and append it to the :py:attr:`lazyscribe.experiment.Experiment.tests` list:

.. code-block:: python

    from lazyscribe import Test

    with project.log(name="My experiment") as exp:
        test = Test(name="My test", description="Demo test")
        test.log_metric("metric", 0.3)
        exp.tests.append(test)

Logging artifacts to a test
----------------------------

Tests support the same artifact system as experiments. Use
:py:meth:`lazyscribe.test.Test.log_artifact` to associate an artifact with a test:

.. code-block:: python

    from lazyscribe import Project

    project = Project(fpath="project.json", mode="w")

    with project.log(name="My experiment") as exp:
        with exp.log_test(name="My test") as test:
            test.log_metric("metric", 0.9)
            test.log_artifact(name="predictions", value=[0, 1, 1, 0], handler="json")

    project.save()

Artifacts are **not** written to disk when you call
:py:meth:`lazyscribe.test.Test.log_artifact` — they are only persisted when you call
:py:meth:`lazyscribe.project.Project.save`. Test artifact files are stored inside a
subdirectory of the experiment's folder, named after the slugified test name (e.g.
``my-experiment-YYYYMMDDHHMMSS/my-test/``).

See :doc:`artifact` for the full list of built-in artifact handlers.

Loading artifacts from a test
------------------------------

To load a test artifact, open the project and call
:py:meth:`lazyscribe.test.Test.load_artifact` on the test object:

.. code-block:: python

    from lazyscribe import Project

    project = Project(fpath="project.json", mode="r")
    exp = project["my-experiment"]
    test = exp.tests[0]
    predictions = test.load_artifact(name="predictions")

As with experiment artifacts, you can disable runtime environment validation with
``validate=False``:

.. code-block:: python

    predictions = test.load_artifact(name="predictions", validate=False)
