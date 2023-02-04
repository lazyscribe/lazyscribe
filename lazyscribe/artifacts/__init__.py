"""Import the handlers."""

from typing import List

from .base import Artifact
from .json import JSONArtifact
from .sklearn import SklearnArtifact

__all__: List[str] = ["Artifact", "JSONArtifact", "SklearnArtifact"]
