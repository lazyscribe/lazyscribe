Specify cross-project dependencies
==================================

In this guide, we will walk through specifying cross-project experiment dependencies.
This feature can be useful if you have multiple linked projects.

To specify an upstream experiment dependency, you can add an entry to the ``dependencies``
list in your experiment. Add an experiment with the format ``<PATH_TO_PROJECT_JSON>|<SLUG>``.
So, if you created an experiment in ``other-project.json`` at 9:30 AM on Jan 1, 2022 with the
name "My experiment", you would have

.. code-block:: json
    :emphasize-lines: 5-7

    [
        {
            ...,
            "dependencies": [
                "other-project.json|my-experiment-20220101093000"
            ],
            "name": "Base performance",
            "short_slug": "base-performance",
            "slug": "base-performance-<TIMESTAMP>",
            ...
        }
    ]

.. important::

    ``other-project.json`` is the path provided the :py:class:`lazyscribe.project.Project`
    when ``my-experiment`` was loaded and added as a dependency. It is either relative
    to the working directory or an absolute path (often the case with remote filesystems
    like S3).


When you load the experiment through :py:class:`lazyscribe.project.Project`, the dependencies
will be accessible through a dictionary, using the ``short_slug`` as a key:

.. code-block:: python

    from lazyscribe import Project

    project = Project(..., mode="r")
    exp = project["base-performance"]

    assert "my-experiment" in exp.dependencies

You can also add a dependency in python:

.. code-block:: python

    from lazyscribe import Project

    myproject = Project(..., mode="w+")
    otherproject = Project(...)

    exp = myproject["base-performance"]
    exp.dependencies["my-experiment"] = otherproject["my-experiment"]
