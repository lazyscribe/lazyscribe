Log non-global metrics
======================

Sometimes, it's helpful to log non-global metrics to an experimenent. To do so, create a
:py:class:`lazyscribe.Test` using :py:meth:`lazyscribe.Experiment.log_test`:

.. code-block:: python

    from lazyscribe import Project

    project = Project(fpath="project.json", mode="w")

    with project.log(name="My experiment") as exp:
        with exp.log_test(name="My test", description="Demo test") as test:
            test.log_metric("metric", 0.3)

The :py:meth:`Experiment.log_test` context handler creates a :py:class:`Test` object and
logs it back to the experiment when the handler exits. If you want to avoid using the context
handler, instantiate your own test and append it to the ``tests`` list:

.. code-block:: python

    from lazyscribe import Test

    with project.log(name="My experiment") as exp:
        test = Test(name="My test", description="Demo test")
        test.log_metric("metric", 0.3)
        exp.tests.append(test)
