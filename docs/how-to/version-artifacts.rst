Version artifacts
=================

This guide will walk you through the process of using :py:class:`lazyscribe.repository.Repository`
to access and version artifacts across projects.

    A :py:class:`lazyscribe.repository.Repository` is an organized structure that stores and versions
    your artifacts.

Using a repository as a standalone structure
--------------------------------------------

If you have artifacts and/or objects that were generated outside of the ``lazyscribe`` ecosystem,
you can still use them with the :py:class:`lazyscribe.repository.Repository` structure. Similar to the guide
on :doc:`saving artifacts with experiments <artifact>`, we will use
:py:meth:`lazyscribe.repository.Repository.log_artifact`:

.. code-block:: python

    from lazyscribe import Repository

    repository = Repository("repository.json", mode="w")
    repository.log_artifact(name="features", value=[0, 1, 2], handler="json", indent=4)

    repository.save()

After :py:meth:`lazyscribe.repository.Repository.log_artifact`, the value ``[0, 1, 2]`` will be associated
with the repository. However, it won't appear as a JSON file until you call
:py:meth:`lazyscribe.repository.Repository.save`. You can retrieve the artifact using
:py:meth:`lazyscribe.repository.Repository.load_artifact`:

.. code-block:: python

    from lazyscribe import Repository

    repository = Repository("repository.json", mode="r")  # read-only mode
    features = repository.load_artifact(name="features")

So, what's the big deal? In the repository class, you can log artifacts with overlapping names. Each
artifact is assigned an integer version number as well as a creation date, allowing you to time-travel
between versions.

.. code-block:: python

    from lazyscribe import Repository

    # append-only mode reads in the existing repository and allows for new artifacts
    repository = Repository("repository.json", mode="a")
    repository.log_artifact(name="features", value=[0, 1, 2, 3], handler="json", indent=4)

    repository.save()

Now we have two versions of the same ``features`` artifact. There are multiple ways to load a specific
version of your artifact.

.. code-block:: python

    from lazyscribe import Repository

    repository = Repository("repository.json", mode="r")

    # Without any additional parameters, Repository will retrieve the most recent version
    newest = repository.load_artifact("features")

    # You can specify a specific integer version (0-indexed)
    oldest = repository.load_artifact("features", version=0)

    # Or the exact datetime
    on_this_date = repository.load_artifact("features", version="YYYY-MM-DDTHH:MM:SS")

    # To "time-travel", use `match="asof"` with a datetime version to get the most recent version
    # as of the given date
    as_of_this_date = repository.load_artifact("features", version="YYYY-MM-DDTHH:MM:SS", match="asof")

Promote artifacts from experiments to the repository
----------------------------------------------------

Model experimentation is meant to be ephemeral. The Repository provides us with a structure to deploy
and track versions of artifacts over time. So, how do these systems interact?

We can use :py:meth:`lazyscribe.experiment.Experiment.promote_artifact` to associate an artifact with a repository.
The notion is that you may want to deploy/version the artifacts from the most successful experiment in
a project. Here's how you use it.

First, let's create a project and log an experiment:

.. code-block:: python

    from lazyscribe import Project

    project = Project("project.json")
    with project.log("my-experiment") as exp:
        exp.log_artifact(name="features", value=[0, 1, 2], handler="json", indent=4)

    project.save()

Now, let's reload that project and promote the artifact to the repository:

.. code-block:: python

    from lazyscribe import Project, Repository

    project = Project("project.json", mode="r")
    repository = Repository("repository.json")

    project["my-experiment"].promote_artifact(repository, "features")

If you are calling :py:meth:`lazyscribe.experiment.Experiment.promote_artifact` after re-loading a project,
the method

#. copies the artifact from the experiment filesystem location to the repository filesystem location, and
#. calls :py:meth:`lazyscribe.repository.Repository.save` to ensure ``repository.json`` is "in sync" with the filesystem.

If you log the artifact to an experiment and call :py:meth:`lazyscribe.experiment.Experiment.promote_artifact` *before*
calling :py:meth:`lazyscribe.project.Project.save`, it will behave exactly as if you called
:py:meth:`lazyscribe.repository.Repository.log_artifact` -- *you* will be responsible for calling
:py:meth:`lazyscribe.repository.Repository.save`.
