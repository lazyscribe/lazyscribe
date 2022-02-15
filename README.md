# Lightweight, lazy experiment logging

``lazyscribe`` is a lightweight package for model experiment logging. It creates a single JSON
file per project, and an experiment is only added to the file when code finishes (errors won't
result in partially finished experiments in your project log).

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

project = Project(fpath="project.json")
with project.log(name="My experiment") as exp:
    exp.log_metric("auroc", 0.5)
    exp.log_parameter("algorithm", "lightgbm")
```

You've created an experiment! To view the experimental data, call ``to_dict``:

```python
project["my-experiment"].to_dict()
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

Once you've finished, save the project to ``project.json``:

```python
project.save()
```

Later on, you can read the project back in read-only mode ("r"), append mode ("a"),
or editable mode ("w+"):

```python
project = Project("project.json", mode="r")
with project.log(name="New experiment") as exp:  # Raises a RuntimeError
    ...
```
