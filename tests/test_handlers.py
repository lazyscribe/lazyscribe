"""Test the artifact handlers."""

import zoneinfo
from datetime import datetime

import pytest
import time_machine
import yaml

from lazyscribe.artifacts import _get_handler
from lazyscribe.artifacts.joblib import JoblibArtifact
from lazyscribe.artifacts.json import JSONArtifact
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
def test_joblib_handler(tmp_path):
    """Test reading and writing scikit-learn estimators with the joblib handler."""
    joblib = pytest.importorskip("joblib")
    sklearn = pytest.importorskip("sklearn")
    datasets = pytest.importorskip("sklearn.datasets")
    svm = pytest.importorskip("sklearn.svm")

    # Fit a basic estimator
    X, y = datasets.make_classification(n_samples=100, n_features=10)
    estimator = svm.SVC(kernel="linear")
    estimator.fit(X, y)

    # Construct the handler and write the estimator
    location = tmp_path / "my-estimator-location"
    location.mkdir()
    handler = JoblibArtifact.construct(name="My estimator", value=estimator)

    assert (
        handler.fname
        == f"my-estimator-{datetime.now().strftime('%Y%m%d%H%M%S')}.joblib"
    )

    with open(location / handler.fname, "wb") as buf:
        handler.write(estimator, buf)

    assert (location / handler.fname).is_file()

    # Read the estimator back and ensure it's fitted
    with open(location / handler.fname, "rb") as buf:
        out = handler.read(buf)

    sklearn.utils.validation.check_is_fitted(out)

    # Check that the handler correctly captures the environment variables
    assert (
        JoblibArtifact.construct(
            name="EXCLUDED FROM COMPARISON",
            fname="EXCLUDED FROM COMPARISON",
            value=None,
            created_at=None,
            writer_kwargs=None,
            package="sklearn",
            package_version=sklearn.__version__,
            joblib_version=joblib.__version__,
            version=0,
            dirty=False,
        )
    ) == handler


def test_joblib_handler_error_no_inputs():
    """Test that the joblib handler raises an error when no value or package is provided."""
    with pytest.raises(ValueError):
        _ = JoblibArtifact.construct(name="My artifact")


def test_joblib_handler_invalid_package():
    """Test that the joblib handler raises an error when an invalid package is provided."""
    with pytest.raises(ValueError):
        _ = JoblibArtifact.construct(name="My artifact", package="my_invalid_package")


def test_joblib_handler_raise_attribute_error():
    """Test that the joblib handler raises an error for objects where the package can't be determined."""
    numpy = pytest.importorskip("numpy")

    myarr = numpy.array([])
    with pytest.raises(AttributeError):
        JoblibArtifact.construct(name="My array", value=myarr)


def test_get_handler():
    """Test retrieving a handler."""
    handler = _get_handler("joblib")
    assert handler == JoblibArtifact

    handler = _get_handler("json")
    assert handler == JSONArtifact

    with pytest.raises(ValueError):
        _get_handler("fake-handler")


from unittest.mock import Mock, patch


@patch("lazyscribe.artifacts.entry_points")
def test_get_handler_type_error(mock_entry_points):
    """TODO."""
    mock_plugin = Mock()
    mock_plugin.name = "dummy"

    mock_entry_points.return_value = [mock_plugin]
    with pytest.raises(TypeError):
        _get_handler(alias="dummy")


@patch("lazyscribe.artifacts.entry_points")
def test_get_handler_import_error(mock_entry_points):
    """TODO."""
    mock_plugin_import = Mock()
    mock_plugin_import.name = "dummy"
    mock_plugin_import.load.side_effect = ImportError()

    mock_entry_points.return_value = [mock_plugin_import]
    with pytest.raises(ImportError):
        _get_handler(alias="dummy")
