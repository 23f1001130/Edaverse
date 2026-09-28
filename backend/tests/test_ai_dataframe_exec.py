r"""
Tests for backend/app/services/ai_dataframe_exec.py

This is the sandbox that lets the AI chat feature run a short pandas snippet
against a user's dataset, so `_validate_code`'s AST whitelist is the actual
security boundary of that feature — these tests exist to catch any future
change that accidentally weakens it.

Run from D:\Vs Code\dataflow\backend:
    pytest tests/
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services.ai_dataframe_exec import (
    is_dataframe_question, _validate_code, execute_pandas_code, DATA_DIR,
)


# ---------------------------------------------------------------------------
# is_dataframe_question
# ---------------------------------------------------------------------------
def test_is_dataframe_question_detects_aggregation_language():
    assert is_dataframe_question("What is the average order value by region?") is True
    assert is_dataframe_question("group by customer segment and show totals") is True


def test_is_dataframe_question_rejects_generic_chat():
    assert is_dataframe_question("What does this dataset contain overall?") is False


# ---------------------------------------------------------------------------
# _validate_code — allowed snippets must pass
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("code", [
    "result = df.groupby('region')['sales'].sum()",
    "result = df['age'].mean()",
    "result = df.describe()",
    "result = df.sort_values('sales').head(10)",
    "result = df['category'].value_counts()",
])
def test_validate_code_allows_whitelisted_snippets(code):
    _validate_code(code)  # must not raise


# ---------------------------------------------------------------------------
# _validate_code — the actual security boundary: everything below must be
# rejected before it ever touches a real dataset.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("code", [
    "import os\nresult = os.listdir('.')",
    "from os import system\nresult = system('ls')",
    "result = __import__('os').listdir('.')",
    "def f():\n    return 1\nresult = f()",
    "for i in range(10):\n    pass\nresult = df",
    "while True:\n    pass",
    "result = (lambda: df)()",
    "with open('/etc/passwd') as f:\n    result = f.read()",
    "try:\n    result = df\nexcept Exception:\n    pass",
    "raise ValueError('x')",
    "del df",
    "result = df.to_csv('/tmp/out.csv')",
    "result = df.__class__",
    "result = df._get_value(0, 'x')",
    "print(df)",
    "result = eval('df')",
    "result = exec('1')",
    "result = open('/etc/passwd').read()",
    "os.system('rm -rf /')",
    "result = globals()",
])
def test_validate_code_rejects_escape_attempts(code):
    with pytest.raises(ValueError):
        _validate_code(code)


def test_validate_code_rejects_too_many_statements():
    code = "\n".join([f"x{i} = {i}" for i in range(5)]) + "\nresult = df"
    with pytest.raises(ValueError):
        _validate_code(code)


def test_validate_code_rejects_disallowed_names():
    with pytest.raises(ValueError):
        _validate_code("result = some_secret_variable")


# ---------------------------------------------------------------------------
# execute_pandas_code — validation runs before the dataset is even looked up
# ---------------------------------------------------------------------------
def test_execute_pandas_code_validates_before_touching_dataset():
    # A nonexistent dataset_id would normally raise "Dataset data file not
    # found" — if malicious code raised that same error instead of a
    # validation error, it would mean validation ran after the file lookup.
    with pytest.raises(ValueError, match="Unsupported|not allowed"):
        execute_pandas_code("nonexistent-dataset-id", "import os\nresult = os.getcwd()")


# ---------------------------------------------------------------------------
# execute_pandas_code — end-to-end run against a real local dataset file
# ---------------------------------------------------------------------------
def test_execute_pandas_code_runs_allowed_snippet_end_to_end():
    dataset_id = f"test-{uuid.uuid4()}"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / f"{dataset_id}.csv"
    csv_path.write_text("x,y\n1,10\n2,20\n3,30\n", encoding="utf-8")
    try:
        result = execute_pandas_code(dataset_id, "result = df['x'].sum()")
        assert result["result"] == 6
    finally:
        csv_path.unlink(missing_ok=True)


def test_execute_pandas_code_missing_dataset_raises():
    with pytest.raises(ValueError, match="not found"):
        execute_pandas_code(f"missing-{uuid.uuid4()}", "result = df")
