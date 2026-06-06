"""
Tests for backend/app/services/cleaning.py

Run from D:\Vs Code\dataflow\backend:
    pytest tests/
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd

from app.services.cleaning import apply_fixes, suggest_fixes


# ---------------------------------------------------------------------------
# Helper: minimal schema entry
# ---------------------------------------------------------------------------
def _schema(col: str, col_type: str) -> dict:
    return {"name": col, "type": col_type}


# ---------------------------------------------------------------------------
# 1. suggest_fixes — column with 65% nulls gets a "drop_column" suggestion
# ---------------------------------------------------------------------------
def test_suggest_fixes_high_nulls():
    # 20 rows, 13 nulls → 65% missing, which satisfies the >= 60 threshold
    values = [1.0] * 7 + [np.nan] * 13
    df = pd.DataFrame({"sparse": values})
    schema = [_schema("sparse", "float")]
    fixes = suggest_fixes(df, schema)
    actions = [f["action"] for f in fixes]
    assert "drop_column" in actions
    drop = next(f for f in fixes if f["action"] == "drop_column")
    assert drop["column"] == "sparse"


# ---------------------------------------------------------------------------
# 2. suggest_fixes — numeric column with 20% nulls gets fill_median/knn suggestion
# ---------------------------------------------------------------------------
def test_suggest_fixes_numeric_nulls():
    # Single numeric column → no KNN context → fill_median
    values = [10.0, 20.0, np.nan, 40.0, np.nan]
    df = pd.DataFrame({"score": values})
    schema = [_schema("score", "float")]
    fixes = suggest_fixes(df, schema)
    actions = [f["action"] for f in fixes]
    # With only one numeric column there is no KNN context, so fill_median is used
    assert "fill_median" in actions
    fix = next(f for f in fixes if f["action"] == "fill_median")
    assert fix["column"] == "score"


# ---------------------------------------------------------------------------
# 3. suggest_fixes — categorical column with 20% nulls gets "fill_unknown"
# ---------------------------------------------------------------------------
def test_suggest_fixes_categorical_nulls():
    # 10 rows, 2 nulls → 20% missing
    values = (["red", "green", "blue"] * 3)[:8] + [np.nan, np.nan]
    df = pd.DataFrame({"color": values})
    schema = [_schema("color", "categorical")]
    fixes = suggest_fixes(df, schema)
    actions = [f["action"] for f in fixes]
    assert "fill_unknown" in actions
    fix = next(f for f in fixes if f["action"] == "fill_unknown")
    assert fix["column"] == "color"


# ---------------------------------------------------------------------------
# 4. suggest_fixes — column with leading/trailing spaces gets "trim_whitespace"
# ---------------------------------------------------------------------------
def test_suggest_fixes_whitespace():
    # "  Alice  " has leading and trailing spaces
    values = ["Alice", "  Bob  ", "Carol", " Dave", "Eve  "]
    # Need enough rows for a low unique-ratio to be categorical
    values = values * 40  # 200 rows, 5 unique → ratio 0.025 < 0.05
    df = pd.DataFrame({"name": values})
    schema = [_schema("name", "categorical")]
    fixes = suggest_fixes(df, schema)
    actions = [f["action"] for f in fixes]
    assert "trim_whitespace" in actions
    fix = next(f for f in fixes if f["action"] == "trim_whitespace")
    assert fix["column"] == "name"


# ---------------------------------------------------------------------------
# 5. suggest_fixes — column with extreme outliers gets "cap_outliers"
# ---------------------------------------------------------------------------
def test_suggest_fixes_outliers():
    # Normal cluster 1–10, then two extreme outliers at 1000 / -1000
    base = list(range(1, 11)) * 2   # 20 values tightly clustered
    values = base + [1000, -1000]   # 22 values total, >= 10 required
    df = pd.DataFrame({"amount": values})
    schema = [_schema("amount", "integer")]
    fixes = suggest_fixes(df, schema)
    actions = [f["action"] for f in fixes]
    assert "cap_outliers" in actions
    fix = next(f for f in fixes if f["action"] == "cap_outliers")
    assert fix["column"] == "amount"


# ---------------------------------------------------------------------------
# 6. suggest_fixes — df with duplicate rows gets "drop_duplicates"
# ---------------------------------------------------------------------------
def test_suggest_fixes_duplicates():
    df = pd.DataFrame({
        "id":    [1, 2, 3, 1],
        "value": [10, 20, 30, 10],
    })
    schema = [_schema("id", "integer"), _schema("value", "integer")]
    fixes = suggest_fixes(df, schema)
    actions = [f["action"] for f in fixes]
    assert "drop_duplicates" in actions


# ---------------------------------------------------------------------------
# 7. apply_fixes — fill_median fills nulls with the column median
# ---------------------------------------------------------------------------
def test_apply_fix_fill_median():
    # values: [10, 20, NaN, 40, 50] — median of non-null = 30.0
    df = pd.DataFrame({"score": [10.0, 20.0, np.nan, 40.0, 50.0]})
    schema = [_schema("score", "float")]
    cleaned, log, applied = apply_fixes(df, ["fill_median::score"], schema)
    assert cleaned["score"].isna().sum() == 0
    assert cleaned["score"].iloc[2] == 30.0
    assert "fill_median::score" in applied


# ---------------------------------------------------------------------------
# 8. apply_fixes — drop_column removes the column from the df
# ---------------------------------------------------------------------------
def test_apply_fix_drop_column():
    df = pd.DataFrame({
        "keep":   [1, 2, 3],
        "remove": [np.nan, np.nan, np.nan],
    })
    schema = [_schema("keep", "integer"), _schema("remove", "float")]
    cleaned, log, applied = apply_fixes(df, ["drop_column::remove"], schema)
    assert "remove" not in cleaned.columns
    assert "keep" in cleaned.columns
    assert "drop_column::remove" in applied


# ---------------------------------------------------------------------------
# 9. apply_fixes — trim_whitespace removes leading/trailing spaces from strings
# ---------------------------------------------------------------------------
def test_apply_fix_trim_whitespace():
    df = pd.DataFrame({"city": ["  Paris  ", "London", "  Berlin", "Tokyo  "]})
    schema = [_schema("city", "categorical")]
    # The suggestion id emitted by suggest_fixes is "trim::{col}"
    cleaned, log, applied = apply_fixes(df, ["trim::city"], schema)
    assert cleaned["city"].tolist() == ["Paris", "London", "Berlin", "Tokyo"]
    assert "trim::city" in applied


# ---------------------------------------------------------------------------
# 10. apply_fixes — cap_outliers clips extreme values to IQR fences
# ---------------------------------------------------------------------------
def test_apply_fix_cap_outliers():
    # Tight cluster 10–20, plus two extreme outliers
    base = list(range(10, 21))      # 11 values
    df = pd.DataFrame({"val": base + [500, -500]})
    schema = [_schema("val", "integer")]
    cleaned, log, applied = apply_fixes(df, ["cap_outliers::val"], schema)

    # No value should remain beyond the IQR fences
    q1 = pd.Series(base).quantile(0.25)
    q3 = pd.Series(base).quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    assert cleaned["val"].max() <= upper
    assert cleaned["val"].min() >= lower
    assert "cap_outliers::val" in applied
