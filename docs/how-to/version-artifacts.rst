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

    project = Project("project.json", mode="w")
    with project.log("my-experiment") as exp:
        exp.log_artifact(name="features", value=[0, 1, 2], handler="json", indent=4)

    project.save()

Now, let's reload that project and promote the artifact to the repository:

.. code-block:: python

    from lazyscribe import Project, Repository

    project = Project("project.json", mode="r")
    repository = Repository("repository.json", mode="w+")

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

Automated release creation via ``pyproject.toml``
+++++++++++++++++++++++++++++++++++++++++++++++++

If you have multiple repositories under a single project header, managing groups of artifact-versions along
side the project can be a challenge. We have additional functionality to synchronize your project version
and repositories. Suppose you have the following set up:

.. code-block::

    ├── src
    │   ├── model-1
    │   │   ├── ...
    │   │   ├── repository.json
    │   ├── model-2
    │   │   ├── ...
    │   │   ├── repository.json
    ├── pyproject.toml

we can integrate project metadata with the release files. All we have to do is add a section to our ``pyproject.toml``
that tells Lazyscribe where to look:

.. code-block:: toml

    [project]
    version = "1.0.0"

    ...

    [tool.lazyscribe]
    repositories = [
        "src/model-1/repository.json",
        "src/model-2/repository.json"
    ]

with this configuration, we can create releases for both repositories at once using
:py:meth:`lazyscribe.release.release_from_toml`:

.. code-block:: python

    import lazyscribe.release as lzr

    with open("pyproject.toml") as infile:
        lzr.release_from_toml(infile.read())

we will have two new files in our tree.

.. code-block::
    :emphasize-lines: 5, 9

    ├── src
    │   ├── model-1
    │   │   ├── ...
    │   │   ├── repository.json
    │   │   ├── releases.json
    │   ├── model-2
    │   │   ├── ...
    │   │   ├── repository.json
    │   │   ├── releases.json
    ├── pyproject.toml

These releases will have tag ``v1.0.0``.

Deprecate artifact versions
---------------------------

.. important::

    New in 2.0.

Sometimes, an existing artifact version is no longer valid. Prior to version 2.0,
the only way to handle this situation was deleting the artifact and manually editing
the JSON file.

In 2.0, we've added another option: set an expiry timestamp. Having a temporal value
associated with artifact version deprecation is useful because an ``asof`` search yields
a more accurate representation of the available artifacts at a given point in time.
To set an expiry, use :py:meth:`lazyscribe.repository.Repository.set_artifact_expiry`:

.. code-block:: python

    from lazyscribe import Repository

    repository = Repository("repository.json", mode="w")
    # Logging this artifact on Dec 15, 2025
    repository.log_artifact(name="features", value=[0, 1, 2], handler="json", indent=4)
    repository.set_artifact_expiry("features", 0, "2025-12-25T00:00:00")

    repository.save()

By default, the latest version loaded by :py:meth:`lazyscribe.repository.Repository.load_artifact`
will ignore any versions that are expired relative to *today* (implemented through
:py:meth:`lazyscribe._utils.utcnow`). ``asof`` searches include all artifact
versions that are valid *as of the supplied datetime*:

.. code-block:: python

    # Read in our repository from the previous code block on Jan 1, 2026
    features = repository.load_artifact(
        "features", version="2025-12-20T00:00:00", match="asof"
    )  # This call will load version 0

    # Default loading won't work because the only version expired on Dec 25, 2025
    repository.load_artifact("features")  # Raises lazyscribe.exception.VersionNotFoundError

.. important::

    Loading an artifact with ``match="exact"`` will ignore any expiry information.
