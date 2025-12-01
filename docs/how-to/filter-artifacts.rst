Filter repository artifacts
===========================

.. note::

    New in 2.0.0

In this guide, we'll walk through strategies to filter :py:class:`lazyscribe.repository.Repository`
instances based on a version.

In :doc:`our other documentation on versioning <version-artifacts>`, we discuss how to load different
versions of individual artifacts. In 2.0, we have added a feature to filter an entire
:py:class:`lazyscribe.repository.Repository`, creating a single set of output artifacts.

Datetime filtering
------------------

Many times, we are looking for the latest set of artifacts available *as of* a given date. If you
provide :py:meth:`lazyscribe.repository.Repository.filter` with a datetime value or string, that's exactly
what it will give you:

.. code-block:: python

    from lazyscribe import Repository

    repo = Repository(...)
    new_repo: Repository = repo.filter("2025-01-01T00:00:00")

``new_repo`` is a read-only repository with a maximum of one artifact version per unique name. That version
will be the latest version available as of January 1, 2025.

Explicit versioning
-------------------

Datetime filtering is nice, but what if you want an explicit list of artifact versions?

.. code-block:: python

    from lazyscribe import Repository

    repo = Repository(...)
    new_repo = repo.filter(
        version=[
            ("my-first-artifact", 1),
            ("my-second-artifact", 0),
            ("my-third-artifact", 2)
        ]
    )
