"""Test the artifact handlers."""

import pytest

from attrs import asdict
from lazyscribe.artifacts import JSONArtifact, SklearnArtifact, _get_handler


def test_json_handler(tmp_path):
    """Test reading and writing JSON files with the handler."""
    location = tmp_path / "my-location"
    location.mkdir()

    data = [{"key": "value"}]
    handler = JSONArtifact.construct()
    with open(location / "output.json", "w") as buf:
        handler.write(data, buf)

    assert (location / "output.json").is_file()

    with open(location / "output.json", "r") as buf:
        out = handler.read(buf)

    assert data == out


def test_sklearn_handler(tmp_path):
    """Test reading and writing scikit-learn estimators with the handler."""
    joblib = pytest.importorskip("joblib")
    sklearn = pytest.importorskip("sklearn")
    datasets = pytest.importorskip("sklearn.datasets")
    svm = pytest.importorskip("sklearn.svm")

    # Fit a basic estimator
    X, y = datasets.make_classification(n_samples=100, n_features=10)
    estimator = sklearn.svm.SVC(kernel="linear")
    estimator.fit(X, y)

    # Construct the handler and write the estimator
    location = tmp_path / "my-estimator-location"
    location.mkdir()
    handler = SklearnArtifact.construct()
    with open(location / "estimator.joblib", "wb") as buf:
        handler.write(estimator, buf)

    assert (location / "estimator.joblib").is_file()

    # Read the estimator back and ensure it's fitted
    with open(location / "estimator.joblib", "rb") as buf:
        out = handler.read(buf)

    sklearn.utils.validation.check_is_fitted(out)

    # Check that the handler correctly captures the environment variables
    assert (
        SklearnArtifact(
            sklearn_version=sklearn.__version__, joblib_version=joblib.__version__
        )
    ) == handler


def test_get_handler():
    """Test retrieving a handler."""
    handler = _get_handler("scikit-learn")
    assert handler == SklearnArtifact

    with pytest.raises(ValueError):
        _get_handler("fake-handler")
