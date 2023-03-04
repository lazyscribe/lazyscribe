"""Test the artifact handlers."""

import pytest

from lazyscribe.artifacts import JSONArtifact, SklearnArtifact, _get_handler


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

    with open(location / handler.fname, "r") as buf:
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
    estimator = svm.SVC(kernel="linear")
    estimator.fit(X, y)

    # Construct the handler and write the estimator
    location = tmp_path / "my-estimator-location"
    location.mkdir()
    handler = SklearnArtifact.construct(name="My estimator")

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
        SklearnArtifact(
            name="EXCLUDED FROM COMPARISON",
            fname="EXCLUDED FROM COMPARISON",
            value=None,
            writer_kwargs=None,
            sklearn_version=sklearn.__version__,
            joblib_version=joblib.__version__
        )
    ) == handler


def test_get_handler():
    """Test retrieving a handler."""
    handler = _get_handler("scikit-learn")
    assert handler == SklearnArtifact

    with pytest.raises(ValueError):
        _get_handler("fake-handler")
