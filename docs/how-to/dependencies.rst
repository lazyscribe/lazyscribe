Specify cross-project dependencies
==================================

In this guide, we will walk through specifying cross-project experiment dependencies.
This feature can be useful if you have multiple linked projects.

To specify an upstream experiment dependency, you can add an entry to the ``dependencies``
list in your experiment:

.. code-block:: json
    :emphasize-lines: 5

    [
        {
            "author": "<AUTHOR>",
            "created_at": "<TIMESTAMP>",
            "dependencies": [],
            "last_updated": "<TIMESTAMP>",
            "last_updated_by": "<AUTHOR>",
            "metrics": {},
            "name": "Base performance",
            "parameters": {},
            "short_slug": "base-performance",
            "slug": "base-performance-<TIMESTAMP>"
        }
    ]

In the dependencies list, add an experiment with the format ``<PATH_TO_PROJECT_JSON>|<SLUG>``.
So, if you created an experiment in ``other-project.json`` at 9:30 AM on Jan 1, 2022 with the name
"My experiment", you would have

.. code-block:: json
    :emphasize-lines: 5-7

    [
        {
            "author": "<AUTHOR>",
            "created_at": "<TIMESTAMP>",
            "dependencies": [
                "other-project.json|my-experiment-20220101093000"
            ],
            "last_updated": "<TIMESTAMP>",
            "last_updated_by": "<AUTHOR>",
            "metrics": {},
            "name": "Base performance",
            "parameters": {},
            "short_slug": "base-performance",
            "slug": "base-performance-<TIMESTAMP>"
        }
    ]

.. important::

    The path to ``other-project.json`` is relative to the path to the current project JSON.


When you load the experiment through :py:class:`lazyscribe.Project`, the dependencies
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
