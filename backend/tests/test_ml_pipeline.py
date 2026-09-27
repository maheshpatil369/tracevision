import numpy as np
import pytest

from app.ml.classifier import FaceClassifier, ModelNotTrainedError, cosine_similarity


def _toy_dataset(n_per_class=30, n_features=12, seed=0):
    rng = np.random.default_rng(seed)
    x0 = rng.normal(loc=0.0, scale=1.0, size=(n_per_class, n_features))
    x1 = rng.normal(loc=3.0, scale=1.0, size=(n_per_class, n_features))
    X = np.vstack([x0, x1])
    y = np.array([0] * n_per_class + [1] * n_per_class)
    return X, y


def test_predict_before_training_raises_not_fake_result(tmp_path):
    clf = FaceClassifier(model_dir=str(tmp_path / "models"))
    with pytest.raises(ModelNotTrainedError):
        clf.predict([0.0] * 12)


def test_train_produces_real_metrics_and_persists(tmp_path):
    X, y = _toy_dataset()
    clf = FaceClassifier(model_dir=str(tmp_path / "models"))
    result = clf.train(X, y, algorithm="random_forest", cv_folds=3)
    assert 0.0 <= result.metrics["accuracy"] <= 1.0
    assert result.training_samples == len(y)
    assert result.model_version.startswith("random_forest-")
    # separable synthetic classes should be easy to classify well
    assert result.metrics["f1_score"] > 0.7


def test_predict_after_training_uses_persisted_model(tmp_path):
    X, y = _toy_dataset()
    model_dir = str(tmp_path / "models")
    clf = FaceClassifier(model_dir=model_dir)
    clf.train(X, y, algorithm="logistic_regression", cv_folds=3)

    # New instance loads from disk instead of reusing the in-memory pipeline.
    clf2 = FaceClassifier(model_dir=model_dir)
    out = clf2.predict(list(X[0]))
    assert out["prediction"] in ("0", "1")
    assert out["model_version"].startswith("logistic_regression-")


def test_list_versions_reports_every_trained_model(tmp_path):
    X, y = _toy_dataset()
    model_dir = str(tmp_path / "models")
    clf = FaceClassifier(model_dir=model_dir)
    clf.train(X, y, algorithm="random_forest", cv_folds=3)
    clf.train(X, y, algorithm="logistic_regression", cv_folds=3)
    versions = clf.list_versions()
    assert len(versions) == 2


def test_cosine_similarity_bounds_and_identity():
    a = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, a) == 1.0
    assert cosine_similarity([1, 0], [0, 1]) == 0.0
    assert cosine_similarity([0, 0], [1, 1]) == 0.0  # zero vector -> defined as 0, not NaN
