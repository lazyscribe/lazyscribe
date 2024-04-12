Represent the project as a table
================================

To aid in visualization and comparison, ``lazyscribe`` has a built-in method
:py:meth:`lazyscribe.Project.to_tabular` for generating a ``pandas``-ready format:

.. code-block:: python

    from lazyscribe import Project

    project = Project(fpath=..., mode="r")

    experiments, tests = project.to_tabular()

The ``experiments`` entry in the tuple is a list of dictionaries, with each dictionary
representing a single experiment in the project. It will contain metadata as well as each
metric value and parameters that aren't dictionaries, tuples, or lists. The ``tests`` object
refers to :doc:`non-global metrics <tests>`. Similarly, it will contain some experiment metadata
along with the test-level metrics from the experiment.

To use these lists, convert them to :py:class:`pandas.DataFrame` objects with multi-index column names:

.. code-block:: python

    import pandas as pd

    exp_df = pd.DataFrame(experiments)
    exp_df.columns = pd.MultiIndex.from_tuples(exp_df.columns)

    test_df = pd.DataFrame(tests)
    test_df.columns = pd.MultiIndex.from_tuples(test_df.columns)

To view the experiments themselves as dictionaries, you can either iterate through the project:

.. code-block:: python

    import json

    for exp in project:
        print(json.dumps(exp, indent=4))

or call :py:meth:`lazyscribe.Experiment.to_dict` directly:

.. code-block:: python

    project["my-experiment-slug"].to_dict()
