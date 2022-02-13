"""Import path."""

from ._meta import __version__  # noqa: F401

from typing import List

from .project import Project

__all__: List[str] = ["Project"]
