Log a project to an external file system
========================================

To create a project in an external file system, you will need the path to the filesystem including the protocol,
as well as any storage options your filesystem takes.
See the `fsspec <https://filesystem-spec.readthedocs.io/en/latest/usage.html#instantiate-a-file-system>`_ docs
for example usage and available protocols.

.. code-block:: python

    from lazyscribe import Project
    from typing import Any

    project_path = "s3://path/to/my/project.json"
    storage_options: dict[str, Any] = {
        "username": "user",
        "password": "pswrd"
    }

    project = Project(project_path, mode="w", **storage_options)

From there, you can use your project as normal.

Note that to use some external filesystems, you will need to install additional packages.
See the installation instructions `here <https://filesystem-spec.readthedocs.io/en/latest/index.html#installation>`_
in the ``fsspec`` docs for more information.
