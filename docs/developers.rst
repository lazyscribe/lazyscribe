.. highlight:: shell

Contributing
============

Contributions are welcome and greatly appreciated! Every bit helps, and credit
will always be given.

Types of contributions
----------------------

Report bugs
~~~~~~~~~~~

Report bugs `here <https://github.com/lazyscribe/lazyscribe/issues>`_.

Please include

* your operating system and package version,
* any details about your local setup that might be helpful, and
* steps to reproduce the bug.

Fix bugs
~~~~~~~~

Look through our issues. Anything tagged with ``bug`` and ``help wanted``
is open to whoever wants to implement it.

Implement features
~~~~~~~~~~~~~~~~~~

Any issue tagged with ``enhancement`` and ``help wanted`` is open to whoever
wants to implement it.

Write documentation
~~~~~~~~~~~~~~~~~~~

``lazyscribe`` can `always` use more documentation. If you are writing docstrings,
please make sure to run our QA tools before submitting a PR:

.. code-block:: python

    uv sync --extra qa
    uvx ruff check .
    uvx ruff format .
    uv run mypy lazyscribe

If you're writing sphinx documentation, make sure to build the docs locally and preview
them before submitting a PR:

.. code-block:: python

    uv sync --extra docs
    uv run make docs
    cd docs/
    python -m http.server

Submit feedback
~~~~~~~~~~~~~~~

The best way to send feedback is by opening an issue. If you are proposing a feature,

* explain it in detail,
* keep the scope narrow, and
* remember that this project is volunteer-driven, contributions are welcome!

Get started
-----------

Ready to contribute? Here's how you can set up:

#. Fork the repository on GitHub
#. Clone your fork::

    $ git clone https://github.com/<USERNAME>/lazyscribe.git

#. Add the upstream remote. This saves a reference to the main repository::

    $ git remote add upstream https://github.com/lazyscribe/lazyscribe.git

#. Install your local copy into a virtualenv and use install ``pre-commit`` hooks.
   We recommend using `uv <https://docs.astral.sh/uv/>`_::

    $ uv sync --all-extras --dev --python 3.14
    $ uv run pre-commit install --install-hooks

#. Create a branch for local development::

    $ git checkout -b name-of-branch

#. When you're done making changes, run the tests::

    $ uvx nox

#. You can run the QA tooling before ``pre-commit`` as well::

    $ uvx ruff format .
    $ uvx ruff check .
    $ uv run mypy lazyscribe

#. Commit your changes (using `conventional commits <https://www.conventionalcommits.org/en/v1.0.0/#summary>`_)
   and push your branch to GitHub::

    $ git add .
    $ git commit -m "feat: a detailed description"
    $ git push origin name-of-branch

#. Submit a pull request!
