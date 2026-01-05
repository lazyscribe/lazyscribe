Specify cross-project dependencies
==================================

In this guide, we will walk through specifying cross-project experiment dependencies.
This feature can be useful if you have multiple linked projects.

Basic usage
-----------

To specify an upstream experiment dependency, you can add an entry to the ``dependencies``
list in your experiment. Add an experiment with the format ``<PATH_TO_PROJECT_JSON>|<SLUG>``.
So, if you created an experiment in ``other-project.json`` at 9:30 AM on Jan 1, 2022 with the
name "My experiment", you would have

.. code-block:: json
    :emphasize-lines: 4-6

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

Project registry
----------------

.. important::

    New in 2.0.

If your projects live on different filesystems, or require separate credential handling, we have
a project registry to help with cross-project mapping. This data structure acts as a key-based
reference for projects.

.. code-block:: python

    from lazyscribe import Project
    from lazyscribe.registry import registry

    otherproject = Project(..., mode="r")

    # Add the project to the registry
    registry.add_project("other-project", otherproject)

    # Add the dependency in our downstream project
    myproject = Project(..., mode="w+")
    exp = myproject["base-performance"]
    exp.dependencies["my-experiment"] = otherproject["my-experiment"]

    myproject.save()

On the filesystem, our project will look similar to the following:

.. code-block:: json
    :emphasize-lines: 4-6

    [
        {
            ...,
            "dependencies": [
                "other-project|my-experiment-20220101093000"
            ],
            "name": "Base performance",
            "short_slug": "base-performance",
            "slug": "base-performance-<TIMESTAMP>",
            ...
        }
    ]

Our dependency is mapped to the registry name for the project, not the JSON file itself.

When we load in the project the next time, we need to recreate the registry as a reference. Doing
so gives us the flexibility to reference projects stored across many locations, both local and
remote.

.. code-block:: python

    from lazyscribe import Project
    from lazyscribe.registry import registry

    otherproject = Project(..., mode="r")

    # Add the project to the registry
    registry.add_project("other-project", otherproject)

    myproject = Project(..., mode="r")  # This time, the dependencies will load from the registry

If we try to load the project without creating the registry, the project will treat
``other-project`` as the path to a non-existent JSON file.
