"""Repository releases."""

from attrs import Factory, asdict, define, field

from lazyscribe._utils import serializer, utcnow
from lazyscribe.repository import Repository


@define
class Release:
    """Create a release associated with a Repository instance.

    Parameters
    ----------
    tag : str
        A string descriptor for the release. Commonly coincides with semantic
        or calendar versioning.
    artifacts : list[tuple[str, int]]
        A list of the latest available artifacts and versions in the source repository.
    created_at : datetime.datetime
        The creation timestamp for the release.
    """

    tag: str = field()
    artifacts: list[tuple[str, str]] = field()
    created_at: str = Factory(utcnow)

    def to_dict(self) -> dict[str, list[tuple[str, int]] | str]:
        """Serialize the release to a dictionary.

        Returns
        -------
        dict
            A dictionary with the release information.
        """
        return asdict(self, value_serializer=serializer)


def create_release(repository: Repository, tag: str) -> Release:
    """Create a release.

    A release is a collection of specific artifact versions. It is generated
    by taking the latest available version of each artifact.

    Parameters
    ----------
    repository : lazyscribe.repository.Repository
        The source repository.
    tag : str
        A string descriptor of the tag. Commonly coincides with semantic or calendar
        versioning.

    Returns
    -------
    lazyscribe.release.Release
        The release object.
    """
    all_artifacts_ = sorted({art.name for art in repository.artifacts})

    latest: list[tuple[str, int]] = []
    for name in all_artifacts_:
        art = repository._search_artifact_versions(name)
        latest.append((name, art.version))

    return Release(tag=tag, artifacts=latest)
