r"""
Tests for backend/app/services/eda.py

Run from D:\Vs Code\dataflow\backend:
    pytest tests/
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd

from app.services.eda import (
    is_id_like, compute_correlation, compute_outliers,
    compute_missingness_matrix, compute_target_analysis,
)


def _schema(col: str, col_type: str, null_pct: float = 0.0, null_count: int = 0) -> dict:
    return {"name": col, "type": col_type, "null_pct": null_pct, "null_count": null_count}


def _dataset(df: pd.DataFrame, schema: list) -> dict:
    return {"id": "test-dataset", "schema": schema, "sample_rows": df.to_dict(orient="records")}


# ---------------------------------------------------------------------------
# is_id_like — customer_id-style columns should be recognized and excluded
# ---------------------------------------------------------------------------
def test_is_id_like_recognizes_named_unique_column():
    df = pd.DataFrame({"customer_id": [f"CUST{i}" for i in range(100)]})
    info = _schema("customer_id", "text")
    assert is_id_like(info, df) is True


def test_is_id_like_does_not_flag_normal_numeric_column():
    df = pd.DataFrame({"age": np.random.randint(18, 80, size=100)})
    info = _schema("age", "integer")
    assert is_id_like(info, df) is False


def test_is_id_like_requires_high_uniqueness():
    # Named like an id but heavily repeated values — not actually an id column.
    df = pd.DataFrame({"region_id": ["A", "B"] * 50})
    info = _schema("region_id", "categorical")
    assert is_id_like(info, df) is False


# ---------------------------------------------------------------------------
# compute_correlation — excludes id-like columns from the numeric set
# ---------------------------------------------------------------------------
def test_compute_correlation_excludes_id_like_columns():
    n = 50
    df = pd.DataFrame({
        "customer_id": list(range(n)),  # unique, name-signaled — should be excluded
        "age": np.random.randint(18, 80, size=n),
        "spend": np.random.uniform(10, 500, size=n),
    })
    schema = [_schema("customer_id", "integer"), _schema("age", "integer"), _schema("spend", "float")]
    result = compute_correlation(df, schema)
    assert result is not None
    assert "customer_id" not in result["columns"]
    assert "age" in result["columns"] and "spend" in result["columns"]


# ---------------------------------------------------------------------------
# compute_outliers — IQR-based detection on a column with a clear outlier
# ---------------------------------------------------------------------------
def test_compute_outliers_detects_extreme_value():
    values = [10, 11, 12, 9, 10, 11, 10, 9, 12, 500]
    df = pd.DataFrame({"amount": values})
    schema = [_schema("amount", "integer")]
    outliers = compute_outliers(df, schema)
    amount_result = next((o for o in outliers if o["column"] == "amount"), None)
    assert amount_result is not None
    assert amount_result["count"] >= 1


# ---------------------------------------------------------------------------
# compute_missingness_matrix — only columns that actually have nulls appear
# ---------------------------------------------------------------------------
def test_missingness_matrix_excludes_complete_columns():
    df = pd.DataFrame({
        "complete": [1, 2, 3, 4, 5],
        "sparse": [1, np.nan, 3, np.nan, 5],
    })
    schema = [
        _schema("complete", "integer", null_pct=0.0),
        _schema("sparse", "integer", null_pct=40.0),
    ]
    result = compute_missingness_matrix(df, schema)
    assert result is not None
    assert result["columns"] == ["sparse"]
    assert "complete" not in result["columns"]


def test_missingness_matrix_returns_none_when_nothing_missing():
    df = pd.DataFrame({"complete": [1, 2, 3]})
    schema = [_schema("complete", "integer", null_pct=0.0)]
    assert compute_missingness_matrix(df, schema) is None


# ---------------------------------------------------------------------------
# compute_target_analysis — classification/regression branching, id-like
# exclusion, and the negligible-relationship filter
# ---------------------------------------------------------------------------
def test_target_analysis_classification_excludes_id_and_weak_columns():
    n = 200
    rng = np.random.RandomState(0)
    tenure = rng.uniform(0, 60, size=n)
    # churn strongly driven by low tenure; noise is unrelated to churn
    churn = np.where(tenure < 12, "Yes", "No")
    df = pd.DataFrame({
        "customer_id": [f"C{i}" for i in range(n)],
        "tenure_months": tenure,
        "noise": rng.uniform(0, 1, size=n),
        "churn": churn,
    })
    schema = [
        _schema("customer_id", "text"),
        _schema("tenure_months", "float"),
        _schema("noise", "float"),
        _schema("churn", "categorical"),
    ]
    result = compute_target_analysis(_dataset(df, schema), "churn")
    assert result["target"]["task"] == "classification"
    features = [r["feature"] for r in result["numeric_relationships"]]
    assert "customer_id" not in features
    assert "tenure_months" in features
    # "noise" has ~zero relationship to churn and should be filtered out
    assert "noise" not in features


def test_target_analysis_regression_task_detection():
    n = 100
    rng = np.random.RandomState(1)
    x = rng.uniform(0, 100, size=n)
    y = x * 2 + rng.normal(0, 1, size=n)  # continuous target, strongly related to x
    df = pd.DataFrame({"x": x, "revenue": y})
    schema = [_schema("x", "float"), _schema("revenue", "float")]
    result = compute_target_analysis(_dataset(df, schema), "revenue")
    assert result["target"]["task"] == "regression"
    assert result["distribution"]["type"] == "histogram"
    features = [r["feature"] for r in result["numeric_relationships"]]
    assert "x" in features


def test_target_analysis_missing_target_returns_error():
    df = pd.DataFrame({"a": [1, 2, 3]})
    schema = [_schema("a", "integer")]
    result = compute_target_analysis(_dataset(df, schema), "does_not_exist")
    assert "error" in result
