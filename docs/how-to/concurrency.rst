Run lazyscribe concurrently
===========================

Logging experiments
-------------------

Multithreading
^^^^^^^^^^^^^^

.. note::

    While experimental, we have tested the following functionality
    against free-threaded python (3.13t, 3.14t).

Lazyscribe provides basic support for concurrent experiment logging.
You can reference a :py:class:`lazyscribe.project.Project` object across
threads and log experiments safely:

.. code-block:: python

    import threading

    from lazyscribe import Project

    project = Project("project.json", mode="w")

    def _closure(project, name: str, metric: float):
        with project.log(name) as exp:
            exp.log_metric("metric", metric)

    threads = [
        threading.Thread(target=_closure, args=(project, *params))
        for params in [
            ("First experiment", 0.5),
            ("Second experiment", 0.75),
            ("Third experiment", 1.0)
        ]
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    project["second-experiment"]  # View the second experiment

Multiprocessing
^^^^^^^^^^^^^^^

Using multiprocessing, we can modify :py:class:`lazyscribe.project.Project`. Instead
of using shared state, we create new "projects" that we can merge back to the original.

.. code-block:: python

    from concurrent.futures import ProcessPoolExecutor

    from lazyscribe import Project

    project = Project("project.json", mode="w")

    def _closure(project, name: str, metric: float):
        with project.log(name) as exp:
            exp.log_metric("metric", metric)

        return project

    with ProcessPoolExecutor(max_workers=2) as ppe:
        futures = [
            ppe.submit(_closure, project, *params)
            for params in [
                ("First experiment", 0.5),
                ("Second experiment", 0.75),
                ("Third experiment", 1.0)
            ]
        ]
        outputs_ = [f.result() for f in futures]

    project = project.merge(*outputs_)

Logging tests
-------------

.. note::

    While experimental, we have tested the following functionality
    against free-threaded python (3.13t, 3.14t).

Similar to the functionality described above, ``lazyscribe`` supports logging
tests in parallel threads:

.. code-block:: python

    import threading

    from lazyscribe import Project

    project = Project("project.json", mode="w")

    def _closure(experiment, name: str, metric: float):
        with experiment.log_test(name) as test:
            test.log_metric("metric", metric)

    with project.log(name="My experiment") as exp:
        threads = [
            threading.Thread(target=_closure, args=(exp, *params))
            for params in [
                ("Subpopulation 1", 0.5),
                ("Subpopulation 2", 0.75),
                ("Subpopulation 3", 1.0)
            ]
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

    project["my-experiment"]  # Look at the experiment and associated tests

It's important to note that no other experiment or test-level logging functionality
is thread-safe.
