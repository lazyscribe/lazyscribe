"""Custom exceptions for lazyscribe."""


class ReadOnlyError(Exception):
    """Raised when a project or repository is opened in read-only mode and write operations are tried."""

    pass


class ArtifactError(Exception):
    """Base exception for artifact errors."""

    pass


class ArtifactLogError(Exception):
    """Raised when an artifact cannot be logged."""

    pass


class ArtifactLoadError(Exception):
    """Raised when an artifact cannot be loaded."""

    pass
