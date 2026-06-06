"""
Tests for backend/app/services/parser.py

Run from D:\Vs Code\dataflow\backend:
    pytest tests/
"""

import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd

from app.services.parser import (
    build_column_schema,
    detect_encoding,
    infer_column_type,
    parse_csv,
    parse_file,
)


# ---------------------------------------------------------------------------
# 1. detect_encoding — UTF-8 bytes are identified correctly
# ---------------------------------------------------------------------------
def test_detect_encoding_utf8():
    sample = "id,name,score\n1,Alice,95\n2,Bob,87\n".encode("utf-8")
    result = detect_encoding(sample)
    assert isinstance(result, dict)
    assert "encoding" in result
    assert "confidence" in result
    # chardet reliably identifies plain ASCII-compatible UTF-8
    encoding = result["encoding"].lower().replace("-", "")
    assert "utf" in encoding or "ascii" in encoding
    assert 0.0 <= result["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# 2. infer_column_type — integer series
# ---------------------------------------------------------------------------
def test_infer_integer():
    series = pd.Series([1, 2, 3, 4, 5], dtype="int64")
    assert infer_column_type(series) == "integer"


# ---------------------------------------------------------------------------
# 3. infer_column_type — float series
# ---------------------------------------------------------------------------
def test_infer_float():
    series = pd.Series([1.1, 2.2, 3.3, 4.4, 5.5], dtype="float64")
    assert infer_column_type(series) == "float"


# ---------------------------------------------------------------------------
# 4. infer_column_type — low-cardinality strings return "categorical"
# ---------------------------------------------------------------------------
def test_infer_categorical():
    # 3 unique values across 200 entries → unique_ratio ≈ 0.015 < 0.05, nuniq ≤ 50
    values = (["red", "green", "blue"] * 67)[:200]
    series = pd.Series(values, dtype=object)
    assert infer_column_type(series) == "categorical"


# ---------------------------------------------------------------------------
# 5. infer_column_type — true/false strings return "boolean"
# ---------------------------------------------------------------------------
def test_infer_boolean():
    series = pd.Series(["true", "false", "True", "False", "true"], dtype=object)
    assert infer_column_type(series) == "boolean"


# ---------------------------------------------------------------------------
# 6. infer_column_type — all-NaN series returns "empty"
# ---------------------------------------------------------------------------
def test_infer_empty():
    series = pd.Series([np.nan, np.nan, np.nan], dtype=object)
    assert infer_column_type(series) == "empty"


# ---------------------------------------------------------------------------
# 7. build_column_schema — null_pct is accurate for a column with known nulls
# ---------------------------------------------------------------------------
def test_build_schema_null_pct():
    # 10 rows, 4 nulls → null_pct = 40.0
    data = {"score": [10, 20, np.nan, 40, np.nan, 60, 70, np.nan, 90, np.nan]}
    df = pd.DataFrame(data)
    schema = build_column_schema(df)
    assert len(schema) == 1
    col_info = schema[0]
    assert col_info["name"] == "score"
    assert col_info["null_count"] == 4
    assert col_info["null_pct"] == 40.0


# ---------------------------------------------------------------------------
# 8. parse_csv — basic 3-row CSV has correct shape and column names
# ---------------------------------------------------------------------------
def test_parse_csv_basic():
    csv_text = "id,name,score\n1,Alice,95\n2,Bob,87\n3,Carol,72\n"
    contents = csv_text.encode("utf-8")
    result = parse_csv(contents, encoding="utf-8")
    # Returns (df, warnings)
    df, warnings = result
    assert df.shape == (3, 3)
    assert list(df.columns) == ["id", "name", "score"]
    assert isinstance(warnings, list)


# ---------------------------------------------------------------------------
# 9. parse_csv — TSV file triggers tab delimiter detection
# ---------------------------------------------------------------------------
def test_parse_csv_delimiter_tab():
    tsv_text = "id\tname\tscore\n1\tAlice\t95\n2\tBob\t87\n3\tCarol\t72\n"
    contents = tsv_text.encode("utf-8")
    # sample_only=True returns (df, warnings, delimiter)
    df, warnings, delimiter = parse_csv(contents, encoding="utf-8", sample_only=True)
    assert delimiter == "\t"
    assert df.shape == (3, 3)
    assert list(df.columns) == ["id", "name", "score"]


# ---------------------------------------------------------------------------
# 10. parse_file — returns dict with expected top-level fields
# ---------------------------------------------------------------------------
def test_parse_file_success_fields():
    csv_text = "product,price,units\nwidget,9.99,100\ngadget,24.99,50\ndongle,4.99,200\n"
    contents = csv_text.encode("utf-8")
    result = parse_file("products.csv", contents)

    assert result["success"] is True
    assert "schema" in result
    assert "shape" in result
    assert "sample_rows" in result
    assert result["shape"]["rows"] == 3
    assert result["shape"]["columns"] == 3
    assert isinstance(result["schema"], list)
    assert len(result["schema"]) == 3
    assert isinstance(result["sample_rows"], list)
    assert len(result["sample_rows"]) == 3  # 3 rows, all within SAMPLE_ROWS=5
