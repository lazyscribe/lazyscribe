Write a custom artifact handler
===============================

.. important::

    See :doc:`this guide<artifact>` to understand experiment artifacts in
    ``lazyscribe``.

In this guide, we'll walk through how you can write a custom artifact handler.

Building the handler
--------------------

Each handler is a subclass of :py:class:`lazyscribe.artifacts.base.Artifact`, with
the following mandatory class variables:

#. ``alias``: this is the value used to select the handler when logging
   artifacts (``handler="json"``, for example).
#. ``suffix``: the suffix of the output artifact on disk (e.g. ``json`` for the
   JSON handler).
#. ``binary``: Whether or not the output artifact is a binary file type.
#. ``output_only``: Whether or not the output file can be reconstructed as a
   Python object on read.

Additional class variables are used to capture metadata about the environment
or artifact. Let's create a handler for text files to demonstrate.

.. code-block:: python

    from typing import ClassVar

    from attrs import define
    from slugify import slugify

    from lazyscribe.artifacts.base import Artifact

    @define(auto_attribs=True)
    class TextArtifact(Artifact):
        """Handler for Text artifacts."""

        alias: ClassVar[str] = "text"
        suffix: ClassVar[str] = "txt"
        binary: ClassVar[bool] = False
        output_only: ClassVar[bool] = False

Next, we have to write a ``construct`` method to build our artifact handler. If we had
additional metadata to capture, this is where we would capture it
(see :py:class:`lazyscribe.artifacts.json.JSONArtifact`) for an example. The signature of the
``construct`` method is **fixed**.

.. code-block:: python

    from datetime import datetime, timezone
    from typing import Any, ClassVar, Optional

    from attrs import define

    from lazyscribe.artifacts.base import Artifact

    @define(auto_attribs=True)
    class TextArtifact(Artifact):
        """Handler for Text artifacts."""

        alias: ClassVar[str] = "text"
        suffix: ClassVar[str] = "txt"
        binary: ClassVar[bool] = False
        output_only: ClassVar[bool] = False

        @classmethod
        def construct(
            cls,
            name: str,
            value: Any = None,
            fname: str | None = None,
            created_at: datetime | None = None,
            writer_kwargs: dict | None = None,
            version: int | None = None
            **kwargs
        ):
            """Construct the handler class."""
            created_at = created_at or datetime.now(timezone.utc)
            return cls(
                name=name,
                value=value,
                writer_kwargs=writer_kwargs or {},
                version=version,
                fname=fname or f"{slugify(name)}-{slugify(created_at.strftime('%Y%m%d%H%M%S'))}.{cls.suffix}",
                created_at=created_at,
            )

Finally, we have to write the I/O methods, ``read`` and ``write``. Both of these
methods should expect a file buffer from the ``fsspec`` filesystem.

.. code-block:: python


    @define(auto_attribs=True)
    class TextArtifact(Artifact):
        ...
        @classmethod
        def read(cls, buf, **kwargs):
            """Read in the artifact.

            Parameters
            ----------
            buf : file-like object
                The buffer from a ``fsspec`` filesystem.
            **kwargs
                Keyword arguments for compatibility.

            Returns
            -------
            Any
                The artifact.
            """
            return buf.read()

        @classmethod
        def write(cls, obj, buf, **kwargs):
            """Write the content to a Text file.

            Parameters
            ----------
            obj : object
                The Text-serializable object.
            buf : file-like object
                The buffer from a ``fsspec`` filesystem.
            **kwargs
                Keyword arguments for compatibility.
            """
            buf.write(obj)

You have a new custom handler!

Using the handler
-----------------

There are two ways to make your custom handler visible to ``lazyscribe``.

Entry points (for packages)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can register your artifact handler using entry points in the
``lazyscribe.artifact_type`` group. For example, suppose we distributed our
``TextArtifact`` class as ``myproject.artifacts.TextArtifact``. In the ``pyproject.toml``
for ``myproject``, we can include the following:

.. code-block:: toml

    [project.entry-points."lazyscribe.artifact_type"]
    text = "myproject.artifacts:TextArtifact"

Then, you can use :py:meth:`lazyscribe.Experiment.log_artifact` with ``handler="text"``.

Subclass scanning
~~~~~~~~~~~~~~~~~

If you're experimenting or you're not writing your handler as part of a package, you can
still use the custom handler. All you need to do is make sure the class has been imported
in the module where you are logging experiments:

.. code-block:: python

    from mymodule import TextArtifact

    from lazyscribe import Project

    project = Project(...)

    with project.log_experiment(...) as exp:
        exp.log_artifact(..., handler="text")

This method works by looking for all available subclasses of :py:class:`lazyscribe.artifacts.base.Artifact`
at runtime.
