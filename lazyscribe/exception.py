"""Custom exceptions for lazyscribe."""


class LazyscribeError(Exception):
    """Base exception for lazyscribe errors."""


class ReadOnlyError(LazyscribeError):
    """Raised when a project or repository is opened in read-only mode and write operations are tried."""


class SaveError(LazyscribeError):
    """Raised when a project or repository is unable to save objects to the filesystem."""


class ArtifactError(LazyscribeError):
    """Base exception for artifact errors."""


class ArtifactLogError(ArtifactError):
    """Raised when an artifact cannot be logged."""


class ArtifactLoadError(ArtifactError):
    """Raised when an artifact cannot be loaded."""


class VersionNotFoundError(LazyscribeError):
    """Raised when the version cannot be found."""


class InvalidVersionError(LazyscribeError):
    """Raised when an invalid version is provided."""
