Create a basic project
======================

To create your first project, instantiate the :py:class:`lazyscribe.Project` class.

.. code-block:: python

    from lazyscribe import Project

    project = Project(fpath="project.json", mode="w")

Then, use the context manager to create an experiment and log it back to the project.

.. code-block:: python

    with project.log(name="My experiment") as exp:
        exp.log_metric(...)
        exp.log_parameter(...)

When the context manager exits, the experiment will be appended to the ``Project.experiments`` list.
Using a list allows us to preserve the order and reference a copy when associating it with the project.
If you want to avoid using the context manager, simply instantiate your own experiment and append it
to the ``Project.experiments`` list.

.. code-block:: python

    from lazyscribe import Experiment

    exp = Experiment(name="My experiment", project=project.fpath, author=project.author)
    exp.log_metric(...)
    exp.log_parameter(...)
    project.append(exp)

Once you've finished, save the project to the filesystem using :py:meth:`lazyscribe.Project.save`
method:

.. code-block:: python

    project.save()
