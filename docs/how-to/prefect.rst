Use lazyscribe with Prefect
===========================

`Prefect <https://docs.prefect.io/>`_ is a workflow orchestration tool designed to help reduce negative
engineering. Here, we will describe how you can use ``lazyscribe`` within a Prefect
flow.

In essence, we have created ``prefect`` wrappers around the standard ``lazyscribe``
objects that mimic the native interface within a Prefect flow. Below we have a
basic example of how you might log an experiment.

.. code-block:: python

    from prefect import Flow
    from lazyscribe.prefect import LazyProject

    init_project = LazyProject(fpath=...)
    with Flow(name="My experiment logging") as flow:
        project = init_project()
        with project.log(name="My experiment") as exp:
            exp.log_metric("build_time", "10M")

Let's go through the tasks in this flow.

.. code-block:: python
    :emphasize-lines: 3

    init_project = LazyProject(fpath=...)
    with Flow(name="My experiment logging") as flow:
        project = init_project()

The highlighted task will read (or create) a new project.

.. code-block:: python
    :emphasize-lines: 4

    init_project = LazyProject(fpath=...)
    with Flow(name="My experiment logging") as flow:
        project = init_project()
        with project.log(name="My experiment") as exp:
            exp.log_metric("build_time", "10M")

The context handler will return a :py:class:`lazyscribe.prefect.LazyExperiment`
object, which is a Prefect wrapper on :py:class:`lazyscribe.Experiment` that
mimics the native API.

.. important::

    On exit from the context handler, the experiment will be appended to the
    project. To ensure that the append happens after any interactions with the
    experiment itself, we have added explicit dependencies between the append
    task and any task that is directly downstream from the experiment creation
    (i.e. logging a metric will be downstream of the experiment creation task,
    and will therefore be upstream of the append task).

Finally,

.. code-block:: python
    :emphasize-lines: 5

    init_project = LazyProject(fpath=...)
    with Flow(name="My experiment logging") as flow:
        project = init_project()
        with project.log(name="My experiment") as exp:
            exp.log_metric("build_time", "10M")

The :py:meth:`lazyscribe.prefect.LazyExperiment.log_metric` method will add a
task to log a metric to the experiment.

Outside of basic logging, all other methods are available through
:py:class:`lazyscribe.prefect.LazyProject`. When calling
:py:meth:`lazyscribe.prefect.LazyProject.save` or other such methods, note that
we've inserted an explicit dependency on any task named "Append experiment".
This was done to ensure that the tasks are executed in order.
