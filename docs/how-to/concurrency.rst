Log experiments concurrently
============================

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
