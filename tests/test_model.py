"""Basic tests for the trained model."""

import joblib
import numpy as np
import pytest
from pathlib import Path

MODELS_DIR = Path(__file__).parents[1] / "models"


@pytest.fixture
def model_and_meta():
    """Load the champion model and metadata."""
    model_path = MODELS_DIR / "champion.joblib"
    meta_path = MODELS_DIR / "champion_meta.joblib"
    if not model_path.exists():
        pytest.skip("champion model not available")
    model = joblib.load(model_path)
    meta = joblib.load(meta_path)
    return model, meta


def test_model_loads(model_and_meta):
    model, meta = model_and_meta
    assert model is not None
    assert meta is not None


def test_model_has_features_list(model_and_meta):
    _, meta = model_and_meta
    assert "features" in meta
    assert len(meta["features"]) > 10


def test_model_has_metrics(model_and_meta):
    _, meta = model_and_meta
    assert "metrics" in meta
    assert meta["metrics"]["roc_auc"] > 0.7
    assert meta["metrics"]["pr_auc"] > 0.2


def test_model_predicts(model_and_meta):
    model, meta = model_and_meta
    n_features = len(meta["features"])
    X_dummy = np.zeros((5, n_features))
    proba = model.predict_proba(X_dummy)
    assert proba.shape == (5, 2)
    assert all(0 <= p <= 1 for p in proba[:, 1])


def test_model_outputs_probabilities_sum_to_one(model_and_meta):
    model, meta = model_and_meta
    n_features = len(meta["features"])
    X_dummy = np.random.rand(10, n_features)
    proba = model.predict_proba(X_dummy)
    sums = proba.sum(axis=1)
    np.testing.assert_allclose(sums, 1.0, atol=1e-6)
