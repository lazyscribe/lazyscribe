Filter experiments within your project
======================================

In this guide, we will discuss how you can use a function to iterate through and
filter experiments. First, create a :py:class:`lazyscribe.project.Project`.

.. code-block:: python

    from lazyscribe import Project

    project = Project(fpath="project.json", mode="w")

Then, let's log a couple of experiments.

.. code-block:: python

    with project.log(name="My first experiment") as exp:
        exp.log_metric("metric", 0.75)
        exp.log_parameter("build_period", "10M")

    with project.log(name="My second experiment") as exp:
        exp.log_metric("metric", 0.8)
        exp.log_parameter("build_period", "6M")

    with project.log(name="My third experiment") as exp:
        exp.log_metric("metric", 0.9)
        exp.log_parameter("build_period", "6M")

Suppose you want to look at all experiments with a 6 month build period. We can use
:py:meth:`lazyscribe.project.Project.filter` to do so. All we have to do is write a lambda
function that takes in :py:class:`lazyscribe.experiment.Experiment` and outputs a boolean.

.. code-block:: python

    out_ = list(
        project.filter(func=lambda x: x.parameters["build_period"] == "6M")
    )

This will return our final two experiments as a list of :py:class:`lazyscribe.experiment.Experiment`
objects.
