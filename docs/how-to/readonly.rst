Open existing projects
======================

In this guide, we will walk through the different modes for interacting with an existing
project.

Read-only mode
--------------

If you open a :py:class:`lazyscribe.project.Project` with ``mode="r"``, all experiments will be
loaded into a :py:class:`lazyscribe.experiment.ReadOnlyExperiment` class. You **cannot**

#. set any attributes directly for an experiment,
#. save the project file, or
#. add any experiments to the project.

Append mode
-----------

If you open a project with ``mode="a"``, all existing experiments will be loaded in read-only
mode. However, you **can** add new experiments to the project and save the updated project JSON.

Editable mode
-------------

If you open a project with ``mode="w+"``, you have complete control. All experiments will be loaded
into an editable :py:class:`lazyscribe.experiment.Experiment` class and you can make any changes.

.. note::

    When you save the project, the ``last_updated_by`` experiment attribute will be updated to
    match the ``author`` that opened the project in editable mode.
