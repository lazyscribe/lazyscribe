"""Test the artifact handlers."""

import zoneinfo
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import time_machine
import yaml

from lazyscribe.artifacts import _get_handler
from lazyscribe.artifacts.json import JSONArtifact
from lazyscribe.artifacts.pickle import PickleArtifact
from lazyscribe.artifacts.yaml import YAMLArtifact


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_json_handler(tmp_path):
    """Test reading and writing JSON files with the handler."""
    location = tmp_path / "my-location"
    location.mkdir()

    data = [{"key": "value"}]
    handler = JSONArtifact.construct(name="My output file")

    assert (
        handler.fname
        == f"my-output-file-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    )

    with open(location / handler.fname, "w") as buf:
        handler.write(data, buf)

    assert (location / handler.fname).is_file()

    with open(location / handler.fname) as buf:
        out = handler.read(buf)

    assert data == out


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
@pytest.mark.parametrize(
    "data,Loader",
    (
        ([{"key": "value"}], yaml.SafeLoader),
        ([{"key": "value"}], yaml.FullLoader),
        ([{"type": float}], yaml.FullLoader),
        ({"key": "value", "type": str}, yaml.FullLoader),
    ),
)
def test_yaml_handler(data, Loader, tmp_path):
    """Test reading and writing YAML files with the handler."""
    location = tmp_path / "my-location"
    location.mkdir()
    handler = YAMLArtifact.construct(name="My output file")

    assert (
        handler.fname
        == f"my-output-file-{datetime.now().strftime('%Y%m%d%H%M%S')}.yaml"
    )

    with open(location / handler.fname, "w") as buf:
        handler.write(data, buf)

    assert (location / handler.fname).is_file()

    with open(location / handler.fname) as buf:
        out = handler.read(buf, Loader=Loader)

    assert data == out


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_yaml_handler_defaults_to_safeloader(tmp_path):
    """Test YAML handler defaults to safe loader."""
    location = tmp_path / "my-location"
    location.mkdir()

    data = [{"key": "value"}]
    handler = YAMLArtifact.construct(name="My output file")

    assert (
        handler.fname
        == f"my-output-file-{datetime.now().strftime('%Y%m%d%H%M%S')}.yaml"
    )

    with open(location / handler.fname, "w") as buf:
        handler.write(data, buf)

    assert (location / handler.fname).is_file()

    with open(location / handler.fname) as buf:
        out = handler.read(buf)

    assert data == out

    # Test that it doesn't unserialize objects that need
    # full loader
    data = [{"type": float}]
    handler = YAMLArtifact.construct(name="Unreadable")

    assert handler.fname == f"unreadable-{datetime.now().strftime('%Y%m%d%H%M%S')}.yaml"

    with open(location / handler.fname, "w") as buf:
        handler.write(data, buf)

    assert (location / handler.fname).is_file()

    with (
        open(location / handler.fname) as buf,
        pytest.raises(yaml.constructor.ConstructorError),
    ):
        handler.read(buf)


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_pickle_handler(tmp_path):
    """Test reading and writing pickle artifacts with the handler."""
    location = tmp_path / "my-location"
    location.mkdir()

    data = [{"key": "value"}]
    handler = PickleArtifact.construct(name="My output pickle")

    assert (
        handler.fname
        == f"my-output-pickle-{datetime.now().strftime('%Y%m%d%H%M%S')}.pkl"
    )

    with open(location / handler.fname, "wb") as buf:
        handler.write(data, buf)

    assert (location / handler.fname).is_file()

    with open(location / handler.fname, "rb") as buf:
        out = handler.read(buf)

    assert data == out


def test_get_handler():
    """Test retrieving a handler."""
    handler = _get_handler("json")
    assert handler == JSONArtifact

    with pytest.raises(ValueError):
        _get_handler("fake-handler")


@patch("lazyscribe.artifacts.entry_points")
def test_get_handler_type_error(mock_entry_points):
    """Test raising an error when attempting to retrieve a custom handler through entry points."""
    mock_plugin = Mock()
    mock_plugin.name = "dummy"

    mock_entry_points.return_value = [mock_plugin]
    with pytest.raises(TypeError):
        _get_handler(alias="dummy")


@patch("lazyscribe.artifacts.entry_points")
def test_get_handler_import_error(mock_entry_points):
    """Test raising an import error when retrieving a custom handler through entry points."""
    mock_plugin_import = Mock()
    mock_plugin_import.name = "dummy"
    mock_plugin_import.load.side_effect = ImportError()

    mock_entry_points.return_value = [mock_plugin_import]
    with pytest.raises(ImportError):
        _get_handler(alias="dummy")
