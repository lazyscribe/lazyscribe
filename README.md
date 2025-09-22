[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![PyPI](https://img.shields.io/pypi/v/lazyscribe)](https://pypi.org/project/lazyscribe/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/lazyscribe)](https://pypi.org/project/lazyscribe/) [![Documentation Status](https://github.com/lazyscribe/lazyscribe/actions/workflows/docs.yml/badge.svg)](https://lazyscribe.github.io/lazyscribe/) [![codecov](https://codecov.io/github/lazyscribe/lazyscribe/branch/main/graph/badge.svg?token=M5BHYS2SSU)](https://codecov.io/github/lazyscribe/lazyscribe)

# Lightweight, lazy experiment logging

``lazyscribe`` is a lightweight package for model experiment logging. It creates a single JSON
file per project, and an experiment is only added to the file when code finishes (errors won't
result in partially finished experiments in your project log).

``lazyscribe`` also has functionality to allow for multiple people to work on a single project.
You can merge projects together and update the list of experiments to create a single, authoritative
view of all executed experiments.

# Installation

Python 3.10 and above is required. Use `pip` to install:
```console
$ python -m pip install lazyscribe
```

# Basic Usage

The basic usage involves instantiating a ``Project`` and using the context manager to log
an experiment:

```python
import json

from lazyscribe import Project

project = Project(fpath="project.json")
with project.log(name="My experiment") as exp:
    exp.log_metric("auroc", 0.5)
    exp.log_parameter("algorithm", "lightgbm")
```

You've created an experiment! You can view the experimental data by using ``list``:

```python
print(json.dumps(list(project), indent=4))
```

```json
[
    {
        "name": "My experiment",
        "author": "<AUTHOR>",
        "last_updated_by": "<AUTHOR>",
        "metrics": {
            "auroc": 0.5
        },
        "parameters": {
            "algorithm": "lightgbm"
        },
        "created_at": "<CREATED_AT>",
        "last_updated": "<LAST_UPDATED>",
        "dependencies": [],
        "short_slug": "my-experiment",
        "slug": "my-experiment-<CREATED_AT>",
        "tests": [],
        "artifacts": []
    }
]
```

Once you've finished, save the project to ``project.json``:

```python
project.save()
```

Later on, you can read the project back in read-only mode (`"r"`), append mode (`"a"`),
or editable mode (`"w+"`):

```python
project = Project("project.json", mode="r")
with project.log(name="New experiment") as exp:  # Raises a ReadOnlyError
    ...
```
