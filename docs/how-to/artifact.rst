Save experiment artifacts
=========================

In this guide, we will walk through how you might save additional artifacts
associated with an experiment.

Every experiment has a ``path`` attribute, with the :py:class:`pathlib.Path`
to a unique folder based on experiment slug:

.. code-block:: python

    from lazyscribe import Project

    project = Project()
    with project.log("My experiment") as exp:
        exp.path

This will return ``Path("./my-experiment-YYYYMMDDHHMMSS")``, where the datetime
corresponds to the ``created_at`` attribute.

.. important::

    ``lazyscribe`` does not create the directory for you. You will need to use
    :py:meth:`pathlib.Path.mkdir`.

Artifacts saved to this folder will not be included anywhere in the project JSON file.
It's meant to provide an easy and flexible location for users to save plots, estimators, etc.
