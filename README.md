# Lightweight, lazy experiment logging

``lazyscribe`` is a package for model experiment logging. It's lightweight and "lazy"; it won't
log an experiment to the project until the code is completely finished (errors won't result in
partially finished experiments in your project log). The project logging is human-readable and
concise -- it produces only 1 output file to view.

``lazyscribe`` also has functionality to allow for multiple people to work on a single project.
You can merge projects together and update the list of experiments to create a single, authoritative
view of all executed experiments.

# Installation

```console
$ python -m pip install lazyscribe@git+https://github.com/lazyscribe/lazyscribe
```

# Usage

The basic usage involves instantiating a ``Project`` and using the context manager to log
an experiment:

```python
from lazyscribe import Project

project = Project()
with project.log(name="My experiment") as exp:
    exp.log_metric("auroc", 0.5)
    exp.log_parameter("algorithm", "lightgbm")
```

You've created an experiment! To view the experimental data, call ``to_dict``:

```python
project.experiments[-1].to_dict()
```

```json
{"name": "My experiment",
 "author": "<AUTHOR>",
 "metrics": {"auroc": 0.5},
 "parameters": {"algorithm": "lightgbm"},
 "created_at": "<CREATED_AT>",
 "last_updated": "<LAST_UPDATED>",
 "dependencies": [],
 "short_slug": "my-experiment",
 "slug": "my-experiment-<CREATED_AT>"}
```
