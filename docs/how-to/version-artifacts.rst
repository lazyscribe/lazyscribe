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

Create associated groups of artifact-versions
---------------------------------------------

.. important::

    New in 2.0.0.

While versioning individual artifacts is useful, oftentimes we want to create groups of related assets. These assets
have implicit compatibility, allowing users to time-travel through an entire deployment. We have implemented this
type of functionality through *releases*.

All we need is a repository:

.. code-block:: python

    from lazyscribe import Repository
    from lazyscribe import release as lzr

    repository = Repository(..., mode="r")
    release = lzr.create_release(repository, "v0.1.0")

The output :py:class:`lazyscribe.release.Release` object contains 3 attributes:

* ``tag``: a string identifier for the release. Commonly coincides with semantic versioning.
* ``artifacts``: a list of the latest available artifact names and versions in the repository.
* ``created_at``: a creation timestamp for the release (in UTC).

Then, we can dump this release to a file:

.. code-block:: python

    with open("releases.json", "w") as outfile:
        lzr.dump([release], outfile)

Now, if someone wants to reference the collective group of individual artifact-versions associated with this
release, they can

#. open the repository,
#. load the release, and
#. filter the repository.

In action:

.. code-block:: python

    complete_repository = Repository(..., mode="r")
    with open("releases.json", "r") as infile:
        releases = lzr.load(infile)

    my_release = lzr.find_release(releases, "v0.1.0")

    filtered_repo_ = repository.filter(my_release.artifacts)

``filtered_repo_`` is a read-only version of the original repository object. It will have, at maximum, one
version for each artifact present in the original repository.

Just like artifacts themselves, :py:meth:`lazyscribe.release.find_release` supports ``asof`` matches based
on the release creation timestamp.
