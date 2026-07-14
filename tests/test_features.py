"""Basic tests for the feature engineering pipeline."""

import pandas as pd
import pytest
from pathlib import Path

DATA_PROCESSED = Path(__file__).parents[1] / "data" / "processed"


@pytest.fixture
def features():
    """Load the processed features dataset."""
    path = DATA_PROCESSED / "features.parquet"
    if not path.exists():
        pytest.skip("features.parquet not available")
    return pd.read_parquet(path)


def test_features_not_empty(features):
    assert len(features) > 100_000, f"Expected >100K rows, got {len(features)}"


def test_target_column_exists(features):
    assert "target_oai" in features.columns


def test_target_is_binary(features):
    unique_vals = set(features["target_oai"].unique())
    assert unique_vals <= {0, 1}


def test_oai_rate_reasonable(features):
    rate = features["target_oai"].mean()
    assert 0.01 < rate < 0.20, f"OAI rate {rate:.4f} outside expected range"


def test_no_future_leakage(features):
    """Verify that first inspections have zero prior history."""
    first_inspections = features[features["n_prior_inspections"] == 0]
    assert len(first_inspections) > 0
    assert first_inspections["n_prior_oai"].sum() == 0
    assert first_inspections["n_prior_vai"].sum() == 0
    assert first_inspections["n_prior_nai"].sum() == 0


def test_required_features_present(features):
    required = [
        "fei_number", "inspection_date", "target_oai",
        "n_prior_inspections", "n_prior_oai", "n_prior_vai", "n_prior_nai",
        "days_since_last_inspection", "n_warning_letters", "n_recalls",
        "product_type", "country",
    ]
    missing = [c for c in required if c not in features.columns]
    assert not missing, f"Missing columns: {missing}"


def test_temporal_split_integrity(features):
    """Train/test split should be temporal."""
    features["year"] = features["inspection_date"].dt.year
    train = features[features["year"] < 2025]
    test = features[features["year"] >= 2025]
    assert len(train) > 0
    assert len(test) > 0
    assert train["inspection_date"].max() < test["inspection_date"].min()
