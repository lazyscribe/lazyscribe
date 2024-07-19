from typing import ClassVar, Optional,Any,Dict
from slugify import slugify
from lazyscribe.artifacts import Artifact
from datetime import datetime
# import pytest

# @pytest.fixture
class TestArtifact(Artifact):
    alias: ClassVar[str] = "testartifact"
    suffix: ClassVar[str] = "testartifact"
    binary: ClassVar[bool] = True
    output_only : ClassVar[bool] = True
    python_version: str

    @classmethod
    def construct(
        cls,
        name: str,
        value: Optional[Any] = None,
        fname: Optional[str] = None,
        created_at: Optional[datetime] = None,
        writer_kwargs: Optional[Dict] = None,
        **kwargs,
    ):
        
        return cls(
            name=name,
            value=value,
            writer_kwargs=writer_kwargs or {},
            fname=fname or f"{slugify(name)}.{cls.suffix}",
            created_at=created_at or datetime.now(),
        )

    
    @classmethod
    def read(cls, buf, **kwargs):
        pass


    @classmethod
    def write(cls, obj, buf, **kwargs):
        pass

