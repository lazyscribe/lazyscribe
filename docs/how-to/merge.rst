Merge project files
===================

This guide will walk you through the process of merging multiple project JSON files.
This feature might be useful if multiple people are executing experiments with the
same underlying project.

TL;DR
-----

To perform a project merge, run :py:class:`lazyscribe.Project.merge`:

.. code-block:: python
    :emphasize-lines: 6

    from lazyscribe import Project

    myversion = Project(fpath="project.json")
    otherversion = Project(fpath="other-project.json")

    new = myversion.merge(otherversion)

The new project will take on the ``author`` and ``fpath`` attributes from ``myversion``.
``myversion`` also takes priority for the merge in specific situations.

Appending
---------

``lazyscribe`` will compare experiments in two ways:

#. If the ``slug`` is the same, compare the ``last_updated`` value, or
#. If the ``slug`` is not the same, compare the ``created_at`` value.

Equality is determined by the contents of the entire experiment data. So, appending
new experiments assumes a unique ``slug`` value. Suppose you have the following projects:

.. tab:: Project 1

    .. code-block:: json

        [
            {
                "author": "Me",
                "created_at": "2022-01-01T09:30:00",
                "last_updated": "2022-01-01T09:30:00",
                "last_updated_by": "Me",
                "metrics": {"auroc": 0.4},
                "name": "First experiment",
                "parameters": {},
                "short_slug": "first-experiment",
                "slug": "first-experiment-20220101093000"
            }
        ]

.. tab:: Project 2

    .. code-block:: json

        [
            {
                "author": "Me",
                "created_at": "2022-01-01T09:30:00",
                "last_updated": "2022-01-01T09:30:00",
                "last_updated_by": "Me",
                "metrics": {"auroc": 0.4},
                "name": "First experiment",
                "parameters": {},
                "short_slug": "first-experiment",
                "slug": "first-experiment-20220101093000"
            },
            {
                "author": "My Friend",
                "created_at": "2022-01-05T10:30:00",
                "last_updated": "2022-01-05T10:30:00",
                "last_updated_by": "My Friend",
                "metrics": {"auroc": 0.5},
                "name": "Second experiment",
                "parameters": {"features": ["col1", "col2"]},
                "short_slug": "second-experiment",
                "slug": "second-experiment-20220105103000"
            }
        ]

In this scenario, the first experiment is identical in each project, but Project 2
has a new experiment. The result from the merge will be Project 2's experiment list.

Updating
--------

Suppose you have the following projects:

.. tab:: Project 1

    .. code-block:: json
        :emphasize-lines: 5, 9

        [
            {
                "author": "Me",
                "created_at": "2022-01-01T09:30:00",
                "last_updated": "2022-01-05T11:30:00",
                "last_updated_by": "Me",
                "metrics": {"auroc": 0.4},
                "name": "First experiment",
                "parameters": {"features": ["col1"]},
                "short_slug": "first-experiment",
                "slug": "first-experiment-20220101093000"
            }
        ]

.. tab:: Project 2

    .. code-block:: json

        [
            {
                "author": "Me",
                "created_at": "2022-01-01T09:30:00",
                "last_updated": "2022-01-01T09:30:00",
                "last_updated_by": "Me",
                "metrics": {"auroc": 0.4},
                "name": "First experiment",
                "parameters": {},
                "short_slug": "first-experiment",
                "slug": "first-experiment-20220101093000"
            },
            {
                "author": "My Friend",
                "created_at": "2022-01-05T10:30:00",
                "last_updated": "2022-01-05T10:30:00",
                "last_updated_by": "My Friend",
                "metrics": {"auroc": 0.5},
                "name": "Second experiment",
                "parameters": {"features": ["col1", "col2"]},
                "short_slug": "second-experiment",
                "slug": "second-experiment-20220105103000"
            }
        ]

In this scenario, I forgot to log the ``features`` parameter when I created the experiment, so
I opened it in editable mode a few days later and added it. This means that Project 2 has an outdated
representation of the experiment. When the projects are merged, the newer record will be preserved for
``first-experiment-20220101093000`` and ``second-experiment-20220105103000`` will be added:

.. code-block:: json

    [
        {
            "author": "Me",
            "created_at": "2022-01-01T09:30:00",
            "last_updated": "2022-01-05T11:30:00",
            "last_updated_by": "Me",
            "metrics": {"auroc": 0.4},
            "name": "First experiment",
            "parameters": {"features": ["col1"]},
            "short_slug": "first-experiment",
            "slug": "first-experiment-20220101093000"
        },
        {
            "author": "My Friend",
            "created_at": "2022-01-05T10:30:00",
            "last_updated": "2022-01-05T10:30:00",
            "last_updated_by": "My Friend",
            "metrics": {"auroc": 0.5},
            "name": "Second experiment",
            "parameters": {"features": ["col1", "col2"]},
            "short_slug": "second-experiment",
            "slug": "second-experiment-20220105103000"
        }
    ]

Handling manual updates
~~~~~~~~~~~~~~~~~~~~~~~

Merging updated experiments works well when the user changes the experiment through the python interface.
However, if you choose to edit the project JSON directly, please make sure to update the ``last_updated``
field. If the ``last_updated`` field is not changed, the wrong experiment might persist in the final project.
Here, the merge methodology takes the first project as priority; if you call ``project1.merge(project2)``,
the experiment from ``project1`` will be preserved.
