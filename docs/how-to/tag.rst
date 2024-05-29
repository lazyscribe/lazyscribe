Tag experiments
==========================

In this guide, we will discuss how you can add tags to your experiment. First,
let's create a :py:class:`lazyscribe.Project`.

.. code-block:: python

    from lazyscribe import Project

    project = Project(fpath="project.json", mode="w")

Then, while logging an experiment, we can add our tag using :py:meth:`lazyscribe.Experiment.tag`:

.. code-block:: python

    with project.log(name="My experiment") as exp:
        ...
        exp.tag("success")

We've added a single tag, ``"success"``, to the experiment. We can also add multiple tags
through a single call

.. code-block:: python

    with project.log(name="My experiment") as exp:
        ...
        exp.tag("success", "best-model")

or through multiple calls.

.. code-block:: python

    with project.log(name="My experiment") as exp:
        metric = ...
        if metric > 0.5:
            exp.tag("success")
        if metric > 0.75:
            exp.tag("best-model")

When you call :py:meth:`lazyscribe.Experiment.tag`, you can use ``overwrite=True`` to overwrite
any existing tags.

.. important::

    If you call :py:meth:`lazyscribe.Experiment.tag` with no supplied tags and ``overwrite=True``, you
    will delete all existing tags on the experiment.
