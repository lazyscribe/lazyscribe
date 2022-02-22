Create a basic project
======================

To create your first project, instantiate the :py:class:`lazyscribe.Project` class.

.. code-block:: python

    from lazyscribe import Project

    project = Project()

Then, use the context manager to create an experiment and log it back to the project.

.. code-block:: python

    with project.log(name="My experiment") as exp:
        exp.log_metric(...)
        exp.log_parameter(...)

When the context manager exits, the experiment will be added to the project. If you want
to avoid using the context manager, simply instantiate your own experiment and append it
to the ``Project.experiments`` list.

.. code-block:: python

    from lazyscribe import Experiment

    exp = Experiment(name="My experiment", project=project.fpath, author=project.author)
    exp.log_metric(...)
    exp.log_parameter(...)
    project.experiments.append(exp)
