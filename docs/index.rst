Lightweight, lazy experiment tracking
=====================================

``lazyscribe`` is a lightweight package for model experiment logging. It creates a
single JSON file per project, and an experiment is only added to the log when code
finishes.

``lazyscribe`` also has functionality for merging projects, paving the way for multiple
people to work on a single project.

Installation
------------

To install ``lazyscribe`` from PyPI, run

.. code-block:: console

    $ python -m pip install lazyscribe

This is the preferred method to install ``lazyscribe``.

Contents
--------

.. toctree::
    :maxdepth: 2
    :caption: Quickstart

    tutorials/index

.. toctree::
    :maxdepth: 2
    :caption: How-to...

    how-to/basic
    how-to/tag
    how-to/filter
    how-to/tests
    how-to/tabular
    how-to/artifact
    how-to/custom-artifact
    how-to/dependencies
    how-to/external-fs
    how-to/readonly
    how-to/merge
    how-to/prefect

.. toctree::
    :maxdepth: 2
    :caption: Explanation

.. toctree::
    :maxdepth: 2
    :caption: Reference

    developers
    GitHub repository <https://github.com/lazyscribe/lazyscribe>
    api/modules