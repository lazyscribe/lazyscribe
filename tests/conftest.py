from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from slugify import slugify

from lazyscribe._utils import utcnow
from lazyscribe.artifacts import Artifact


class TestArtifact(Artifact):
    # Tell pytest it's not a Python test class
    __test__ = False
    alias: ClassVar[str] = "testartifact"
    suffix: ClassVar[str] = "testartifact"
    binary: ClassVar[bool] = True
    output_only: ClassVar[bool] = True
    python_version: str

    @classmethod
    def construct(
        cls,
        name: str,
        value: Any | None = None,
        fname: str | None = None,
        created_at: datetime | None = None,
        writer_kwargs: dict | None = None,
        version: int | None = None,
        dirty: bool = False,
        **kwargs,
    ):
        created_at = created_at or utcnow()
        version = version if version is not None else 0
        return cls(
            name=name,
            value=value,
            writer_kwargs=writer_kwargs or {},
            fname=fname
            or f"{slugify(name)}-{created_at.strftime('%Y%m%d%H%M%S')}.{cls.suffix}",
            created_at=created_at,
            version=version,
            dirty=dirty,
        )

    @classmethod
    def read(cls, buf, **kwargs):
        pass

    @classmethod
    def write(cls, obj, buf, **kwargs):
        pass
