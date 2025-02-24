"""Custom exceptions for lazyscribe."""


class LazyscribeError(Exception):
    """Base exception for lazyscribe errors."""


class ReadOnlyError(LazyscribeError):
    """Raised when a project or repository is opened in read-only mode and write operations are tried."""


class ArtifactError(LazyscribeError):
    """Base exception for artifact errors."""


class ArtifactLogError(ArtifactError):
    """Raised when an artifact cannot be logged."""


class ArtifactLoadError(ArtifactError):
    """Raised when an artifact cannot be loaded."""
