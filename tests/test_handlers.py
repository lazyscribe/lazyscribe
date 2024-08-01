"""Test the artifact handlers."""

import pytest

from lazyscribe.artifacts import _get_handler
from lazyscribe.artifacts.joblib import JoblibArtifact
from lazyscribe.artifacts.json import JSONArtifact


def test_json_handler(tmp_path):
    """Test reading and writing JSON files with the handler."""
    location = tmp_path / "my-location"
    location.mkdir()

    data = [{"key": "value"}]
    handler = JSONArtifact.construct(name="My output file")

    assert handler.fname == "my-output-file.json"

    with open(location / handler.fname, "w") as buf:
        handler.write(data, buf)

    assert (location / handler.fname).is_file()

    with open(location / handler.fname) as buf:
        out = handler.read(buf)

    assert data == out


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

    assert handler.fname == "my-estimator.joblib"

    with open(location / handler.fname, "wb") as buf:
        handler.write(estimator, buf)

    assert (location / handler.fname).is_file()

    # Read the estimator back and ensure it's fitted
    with open(location / handler.fname, "rb") as buf:
        out = handler.read(buf)

    sklearn.utils.validation.check_is_fitted(out)

    # Check that the handler correctly captures the environment variables
    assert (
        JoblibArtifact(
            name="EXCLUDED FROM COMPARISON",
            fname="EXCLUDED FROM COMPARISON",
            value=None,
            created_at=None,
            writer_kwargs=None,
            package="sklearn",
            package_version=sklearn.__version__,
            joblib_version=joblib.__version__,
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

    with pytest.raises(ValueError):
        _get_handler("fake-handler")
