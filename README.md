# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/lazyscribe/lazyscribe/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                 |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------- | -------: | -------: | ------: | --------: |
| lazyscribe/\_\_init\_\_.py           |        6 |        0 |    100% |           |
| lazyscribe/\_meta.py                 |        1 |        0 |    100% |           |
| lazyscribe/\_utils.py                |       54 |        0 |    100% |           |
| lazyscribe/artifacts/\_\_init\_\_.py |       20 |        0 |    100% |           |
| lazyscribe/artifacts/base.py         |       47 |        0 |    100% |           |
| lazyscribe/artifacts/json.py         |       25 |        0 |    100% |           |
| lazyscribe/artifacts/pickle.py       |       30 |        0 |    100% |           |
| lazyscribe/exception.py              |        8 |        0 |    100% |           |
| lazyscribe/experiment.py             |      165 |        3 |     98% |287, 510, 519 |
| lazyscribe/linked.py                 |       44 |        0 |    100% |           |
| lazyscribe/project.py                |      208 |        5 |     98% |186, 188, 336-339, 422 |
| lazyscribe/registry.py               |       25 |        0 |    100% |           |
| lazyscribe/release.py                |      126 |        3 |     98% |25, 106, 108 |
| lazyscribe/repository.py             |      220 |        6 |     97% |101, 499, 501, 578-580 |
| lazyscribe/test.py                   |       64 |        2 |     97% |  159, 176 |
| **TOTAL**                            | **1043** |   **19** | **98%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/lazyscribe/lazyscribe/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/lazyscribe/lazyscribe/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/lazyscribe/lazyscribe/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/lazyscribe/lazyscribe/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Flazyscribe%2Flazyscribe%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/lazyscribe/lazyscribe/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.