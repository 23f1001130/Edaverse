import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from app.services.store import ensure_dataset_file

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "datasets"

ALLOWED_METHODS = {
    "abs", "agg", "astype", "corr", "count", "describe", "dropna", "fillna",
    "groupby", "head", "idxmax", "idxmin", "max", "mean", "median", "min",
    "nlargest", "nsmallest", "nunique", "quantile", "reset_index", "round",
    "size", "sort_index", "sort_values", "std", "sum", "tail", "to_frame",
    "value_counts",
}
ALLOWED_NAMES = {"df", "result", "True", "False", "None"}


def is_dataframe_question(question: str) -> bool:
    q = question.lower()
    signals = (
        "group by", "groupby", " by ", "correlation", "correlate", "average",
        "mean", "median", "sum", "total", "top", "bottom", "rank", "compare",
        "breakdown", "distribution", "value counts", "count by", "highest",
        "lowest", "relationship",
    )
    return any(s in q for s in signals)


def _active_dataset_path(dataset_id: str) -> Path | None:
    parquet = DATA_DIR / f"{dataset_id}.parquet"
    if not parquet.exists():
        ensure_dataset_file(dataset_id, parquet.name)
    if parquet.exists():
        return parquet
    csv_path = DATA_DIR / f"{dataset_id}.csv"
    if not csv_path.exists():
        ensure_dataset_file(dataset_id, csv_path.name)
    if csv_path.exists():
        return csv_path
    return None


def _validate_code(code: str) -> None:
    tree = ast.parse(code)
    if len(tree.body) > 3:
        raise ValueError("Only short pandas snippets are allowed.")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                             ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try,
                             ast.Raise, ast.Lambda, ast.Global, ast.Nonlocal, ast.Delete)):
            raise ValueError(f"Unsupported code construct: {node.__class__.__name__}")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_") or node.attr not in ALLOWED_METHODS:
                raise ValueError(f"Unsupported pandas operation: {node.attr}")
        if isinstance(node, ast.Name):
            if node.id not in ALLOWED_NAMES:
                raise ValueError(f"Unsupported name: {node.id}")
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                raise ValueError(f"Direct function calls are not allowed: {func.id}")
            if isinstance(func, ast.Attribute) and func.attr not in ALLOWED_METHODS:
                raise ValueError(f"Unsupported call: {func.attr}")


def execute_pandas_code(dataset_id: str, code: str, timeout: int = 8) -> dict:
    _validate_code(code)
    dataset_path = _active_dataset_path(dataset_id)
    if dataset_path is None:
        raise ValueError("Dataset data file not found.")

    runner = f"""
import json
import pandas as pd

path = {str(dataset_path)!r}
if path.endswith(".parquet"):
    df = pd.read_parquet(path)
else:
    df = pd.read_csv(path)

{code}

def pack(value):
    if hasattr(value, "to_dict"):
        try:
            if hasattr(value, "reset_index"):
                value = value.reset_index()
            if hasattr(value, "head"):
                value = value.head(50)
            return value.to_dict(orient="records")
        except TypeError:
            return value.to_dict()
    if hasattr(value, "item"):
        return value.item()
    return value

print(json.dumps({{"result": pack(result)}}, default=str))
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as f:
        f.write(runner)
        script = f.name
    try:
        proc = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            raise ValueError(proc.stderr.strip()[:500] or "Pandas execution failed.")
        return json.loads(proc.stdout.strip())
    finally:
        try:
            Path(script).unlink()
        except Exception:
            pass
