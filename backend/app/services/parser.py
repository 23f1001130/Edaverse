import io
import csv
import json
import logging
from pathlib import Path
import chardet
import pandas as pd
import numpy as np
from typing import Any

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "datasets"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_ROWS = 5

SMALL_FILE_THRESHOLD = 50 * 1024 * 1024  # 50MB — below this, load fully
CHUNK_SIZE = 10_000  # rows per chunk for large files
SAMPLE_SIZE = 10_000  # rows to sample for schema inference on large files
TEXT_EXTENSIONS = ("csv", "tsv", "txt", "", "json")
logger = logging.getLogger(__name__)


def _finite_numeric(series: pd.Series) -> pd.Series:
    """Return numeric values with NaN/inf removed before stats."""
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()


def _compute_stats_chunked(filepath_or_buffer, delimiter: str, encoding: str, schema_cols: list) -> dict:
    """Compute null counts and numeric stats over a large CSV in chunks.
    Returns {col: {null_count, total, min, max, sum, count}} for numeric cols."""
    stats = {c: {"null_count": 0, "total": 0, "min": None, "max": None,
                 "sum": 0.0, "count": 0} for c in schema_cols}
    try:
        for chunk in pd.read_csv(
            filepath_or_buffer, sep=delimiter, encoding=encoding,
            chunksize=CHUNK_SIZE, on_bad_lines="skip", low_memory=True
        ):
            for col in schema_cols:
                if col not in chunk.columns:
                    continue
                s = stats[col]
                s["total"] += len(chunk[col])
                s["null_count"] += int(chunk[col].isna().sum())
                numeric = _finite_numeric(chunk[col])
                if len(numeric) > 0:
                    cmin = float(numeric.min())
                    cmax = float(numeric.max())
                    s["min"] = cmin if s["min"] is None else min(s["min"], cmin)
                    s["max"] = cmax if s["max"] is None else max(s["max"], cmax)
                    s["sum"] += float(numeric.sum())
                    s["count"] += len(numeric)
    except (pd.errors.ParserError, OSError, UnicodeDecodeError, ValueError, KeyError, TypeError):
        pass
    return stats


def _patch_schema_with_chunked_stats(schema: list, stats: dict) -> list:
    """Replace schema null/min/max/mean with chunked-computed values."""
    for col_info in schema:
        col = col_info["name"]
        if col not in stats:
            continue
        s = stats[col]
        if s["total"] > 0:
            col_info["null_count"] = s["null_count"]
            col_info["null_pct"] = round(s["null_count"] / s["total"] * 100, 1)
        if s["count"] > 0:
            col_info["min"] = round(s["min"], 4) if s["min"] is not None else None
            col_info["max"] = round(s["max"], 4) if s["max"] is not None else None
            col_info["mean"] = round(s["sum"] / s["count"], 4)
    return schema



def detect_encoding(contents: bytes) -> dict:
    detected = chardet.detect(contents)
    return {
        "encoding": detected.get("encoding") or "utf-8",
        "confidence": round(detected.get("confidence") or 0.0, 2),
    }


def infer_column_type(series: pd.Series) -> str:
    if series.dtype == "bool":
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # Try parsing as datetime
    if series.dtype == object:
        # Flatten any unhashable types (lists, dicts from Excel array cells)
        has_unhashable = series.dropna().apply(lambda x: isinstance(x, (list, dict, set))).any()
        if has_unhashable:
            series = series.apply(lambda x: str(x) if isinstance(x, (list, dict, set)) else x)

        non_null = series.dropna()
        if len(non_null) == 0:
            return "empty"

        sample = non_null.head(50)

        # Try datetime
        try:
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
            if parsed.notna().sum() / len(sample) > 0.8:
                return "datetime"
        except (TypeError, ValueError):
            pass

        # Try boolean
        try:
            bool_vals = {"true", "false", "yes", "no", "1", "0", "t", "f"}
            if set(sample.astype(str).str.lower().unique()).issubset(bool_vals):
                return "boolean"
        except (TypeError, AttributeError):
            pass

        # Check cardinality — low = categorical
        try:
            nuniq = series.nunique()
            unique_ratio = nuniq / max(len(non_null), 1)
            if unique_ratio < 0.05 and nuniq <= 50:
                return "categorical"
        except TypeError:
            pass

        return "text"

    return str(series.dtype)


def build_column_schema(df: pd.DataFrame) -> list[dict]:
    schema = []
    for col in df.columns:
        series = df[col]
        total = len(series)
        null_count = int(series.isna().sum())

        col_type = infer_column_type(series)

        col_info: dict[str, Any] = {
            "name": col,
            "type": col_type,
            "null_count": null_count,
            "null_pct": round(null_count / total * 100, 1) if total > 0 else 0,
        }

        # Extra stats per type
        non_null = series.dropna()
        if col_type in ("integer", "float") and len(non_null) > 0:
            def safe_float(v):
                try:
                    f = float(v)
                    if f != f or f == float('inf') or f == float('-inf'):
                        return None
                    return f
                except (TypeError, ValueError, OverflowError):
                    return None
            numeric = _finite_numeric(non_null)
            if len(numeric) == 0:
                schema.append(col_info)
                continue
            col_info["min"] = safe_float(numeric.min())
            col_info["max"] = safe_float(numeric.max())
            col_info["mean"] = safe_float(round(float(numeric.mean()), 4))
            col_info["std"] = safe_float(round(float(numeric.std()), 4)) if len(numeric) > 1 else None
            col_info["median"] = safe_float(round(float(numeric.median()), 4))
            col_info["q25"] = safe_float(round(float(numeric.quantile(0.25)), 4))
            col_info["q75"] = safe_float(round(float(numeric.quantile(0.75)), 4))
            col_info["skewness"] = safe_float(round(float(numeric.skew()), 4)) if len(numeric) > 2 else None

        if col_type in ("categorical", "text", "boolean"):
            try:
                nn = series.dropna()
                nuniq = int(nn.nunique())
                col_info["unique"] = nuniq
                if len(nn) > 0:
                    vc = nn.value_counts()
                    col_info["top"] = str(vc.index[0])
                    col_info["freq"] = int(vc.iloc[0])
                    col_info["freq_pct"] = round(vc.iloc[0] / len(nn) * 100, 1)
                    col_info["top_values"] = [str(v) for v in vc.head(5).index.tolist()]
            except (TypeError, KeyError, ValueError):
                pass

        schema.append(col_info)

    return schema


def get_raw_rows(contents: bytes, ext: str, encoding: str, n: int = 8) -> list:
    """Return the first N rows of the file WITHOUT treating any as a header.
    Used to let the user pick the real header row."""
    try:
        if ext in ("xlsx", "xls"):
            raw = pd.read_excel(io.BytesIO(contents), engine="openpyxl", header=None, nrows=n)
        else:
            text = contents.decode(encoding, errors="replace")
            raw = pd.read_csv(io.StringIO(text), header=None, nrows=n, on_bad_lines="skip", dtype=str)
        rows = []
        for i in range(len(raw)):
            cells = ["" if pd.isna(v) else str(v) for v in raw.iloc[i].tolist()]
            rows.append({"index": i, "cells": cells[:12]})
        return rows
    except (pd.errors.ParserError, OSError, ValueError, UnicodeDecodeError, TypeError):
        return []


def _row_looks_like_header(cells: list) -> float:
    """Score 0-1 how header-like a row is. Higher = more likely a header."""
    vals = [c for c in cells if c and str(c).strip()]
    if not vals:
        return 0.0
    n = len(cells)
    filled = len(vals) / n if n else 0
    # headers are mostly unique
    uniq = len(set(str(v).strip().lower() for v in vals)) / len(vals)
    # headers are mostly non-numeric (column names rarely pure numbers/dates)
    def is_numlike(v):
        v = str(v).strip()
        try:
            float(v.replace(",", ""))
            return True
        except ValueError:
            return False
    non_num = sum(1 for v in vals if not is_numlike(v)) / len(vals)
    # short-ish text tokens score higher than long sentences
    short = sum(1 for v in vals if len(str(v)) <= 30) / len(vals)
    return 0.30 * filled + 0.25 * uniq + 0.30 * non_num + 0.15 * short


def detect_header_row(contents: bytes, ext: str, encoding: str, current_df: pd.DataFrame, max_scan: int = 8):
    """Stronger detection: compare the score of the current header against
    candidate data rows. Return (suggested_row, confidence) or (None, 0).
    Works whether or not pandas produced 'Unnamed' columns."""
    raw = get_raw_rows(contents, ext, encoding, n=max_scan)
    if len(raw) < 2:
        return None, 0.0

    # Score the row pandas currently uses as header (row 0 of the raw file)
    scores = [(_row_looks_like_header(r["cells"]), r["index"]) for r in raw]
    if not scores:
        return None, 0.0

    current_score = scores[0][0]
    best_score, best_idx = max(scores, key=lambda x: x[0])

    # Only suggest if a LATER row clearly beats row 0
    if best_idx > 0 and best_score - current_score > 0.18:
        return best_idx, round(best_score - current_score, 2)

    # Also fire on the classic empty-header case
    unnamed = sum(1 for c in current_df.columns if str(c).startswith("Unnamed"))
    if unnamed >= len(current_df.columns) * 0.4 and best_idx > 0:
        return best_idx, 0.5

    return None, 0.0


def _legacy_detect(df_raw: pd.DataFrame, max_scan: int = 5) -> int | None:
    """Scan first N rows to find the one that looks most like a header.
    Returns row index, or None if the current header seems fine."""
    # If current columns are mostly real (not Unnamed), header is fine
    unnamed = sum(1 for c in df_raw.columns if str(c).startswith("Unnamed"))
    if unnamed < len(df_raw.columns) * 0.4:
        return None

    best_row = None
    best_score = -1
    for i in range(min(max_scan, len(df_raw))):
        row = df_raw.iloc[i]
        non_null = row.notna().sum()
        # header-like: mostly filled, mostly unique, mostly strings
        try:
            unique = row.dropna().astype(str).nunique()
        except (TypeError, ValueError):
            unique = 0
        str_count = sum(1 for v in row if isinstance(v, str))
        score = non_null + unique + str_count
        if score > best_score:
            best_score = score
            best_row = i
    return best_row


def parse_csv(contents: bytes, encoding: str, sample_only: bool = False) -> tuple[pd.DataFrame, list[str]]:
    warnings = []
    text = contents.decode(encoding, errors="replace")

    # Sniff dialect
    try:
        dialect = csv.Sniffer().sniff(text[:4096])
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
        warnings.append("Could not detect delimiter — defaulting to comma")

    nrows = SAMPLE_SIZE if sample_only else None
    try:
        df = pd.read_csv(
            io.StringIO(text),
            sep=delimiter,
            on_bad_lines="warn",
            low_memory=False,
            nrows=nrows,
        )
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError, TypeError) as e:
        logger.warning("CSV parse fallback: %s: %s", type(e).__name__, e)
        warnings.append(f"Parse error: {str(e)}")
        df = pd.read_csv(io.StringIO(text), sep=delimiter, on_bad_lines="skip", nrows=nrows)

    if sample_only:
        warnings.append(f"Large file — schema inferred from first {SAMPLE_SIZE:,} rows. Stats computed over full file.")

    if df.columns.duplicated().any():
        warnings.append("Duplicate column names detected — renamed automatically")

    if sample_only:
        return df, warnings, delimiter
    return df, warnings


def parse_excel(contents: bytes) -> tuple[pd.DataFrame, list[str]]:
    warnings = []
    try:
        df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
    except (ImportError, ValueError, OSError) as exc:
        logger.warning("OpenPyXL parse failed, trying xlrd: %s: %s", type(exc).__name__, exc)
        try:
            df = pd.read_excel(io.BytesIO(contents), engine="xlrd")
        except (ImportError, ValueError, OSError) as e:
            logger.warning("Excel parse failed: %s: %s", type(e).__name__, e)
            raise ValueError(f"Could not parse Excel file: {e}")
    return df, warnings


def parse_parquet(contents: bytes) -> tuple[pd.DataFrame, list[str]]:
    warnings = []
    try:
        df = pd.read_parquet(io.BytesIO(contents))
    except (ImportError, ValueError, OSError) as e:
        logger.warning("Parquet parse failed: %s: %s", type(e).__name__, e)
        raise ValueError(f"Could not parse Parquet file: {e}")
    return df, warnings


def parse_json(contents: bytes, encoding: str) -> tuple[pd.DataFrame, list[str]]:
    warnings = []
    text = contents.decode(encoding, errors="replace")
    try:
        data = json.loads(text)
        if isinstance(data, list):
            # Root-level array — standard case
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Check if any value is a list of objects — e.g. {"colors": [{...}, ...]}
            array_keys = [
                k for k, v in data.items()
                if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict)
            ]
            if array_keys:
                key = array_keys[0]
                df = pd.DataFrame(data[key])
                warnings.append(f'Unwrapped array from key "{key}"')
                if len(array_keys) > 1:
                    warnings.append(f'Multiple array keys found: {array_keys} — used "{key}"')
            else:
                # Flat single object — treat as one-row table
                df = pd.DataFrame([data])
                warnings.append("JSON is a single object — treated as one row")
        else:
            raise ValueError("JSON must be an array or object")
    except json.JSONDecodeError:
        # Try JSON lines
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        try:
            records = [json.loads(l) for l in lines]
            df = pd.DataFrame(records)
            warnings.append("Parsed as JSON lines (newline-delimited JSON)")
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("JSON-lines parse failed: %s: %s", type(e).__name__, e)
            raise ValueError(f"Could not parse JSON: {e}")

    # Flatten nested dicts into dot-notation columns (e.g. rgb.r, rgb.g, rgb.b)
    nested_cols = [c for c in df.columns if df[c].apply(lambda x: isinstance(x, dict)).any()]
    for col in nested_cols:
        try:
            expanded = pd.json_normalize(df[col].tolist())
            expanded.columns = [f"{col}.{c}" for c in expanded.columns]
            df = df.drop(columns=[col]).join(expanded)
            warnings.append(f'Flattened nested object column "{col}" -> {list(expanded.columns)}')
        except (KeyError, TypeError, ValueError):
            pass  # leave as-is if flattening fails

    return df, warnings


def parse_file(filename: str, contents: bytes, header_row: int | None = None) -> dict:
    warnings: list[str] = []
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Encoding detection only matters for text-backed formats. Binary formats get
    # a placeholder so the response shape remains stable.
    enc_info = detect_encoding(contents) if ext in TEXT_EXTENSIONS else {"encoding": None, "confidence": 1.0}
    encoding = enc_info["encoding"]

    if encoding and enc_info["confidence"] < 0.7:
        warnings.append(
            f"Low encoding confidence ({enc_info['confidence']}). "
            f"Detected as {encoding} — may have character errors."
        )

    # Parse by file type
    is_large = len(contents) > SMALL_FILE_THRESHOLD
    delimiter_used = ","
    try:
        if ext in ("xlsx", "xls"):
            if header_row is not None:
                df = pd.read_excel(io.BytesIO(contents), engine="openpyxl", header=header_row)
                parse_warnings = [f"Re-parsed using row {header_row} as header"]
            else:
                df, parse_warnings = parse_excel(contents)
        elif ext == "json":
            df, parse_warnings = parse_json(contents, encoding)
        elif ext == "parquet":
            if header_row is not None:
                warnings.append("Header row selection is ignored for Parquet files")
            df, parse_warnings = parse_parquet(contents)
        elif ext in ("csv", "tsv", "txt", ""):
            if header_row is not None:
                text = contents.decode(encoding, errors="replace")
                try:
                    delimiter_used = csv.Sniffer().sniff(text[:4096]).delimiter
                except csv.Error:
                    delimiter_used = "\t" if ext == "tsv" else ","
                df = pd.read_csv(io.StringIO(text), sep=delimiter_used, header=header_row, on_bad_lines="skip")
                parse_warnings = [f"Re-parsed using row {header_row} as header"]
            elif is_large:
                df, parse_warnings, delimiter_used = parse_csv(contents, encoding, sample_only=True)
            else:
                df, parse_warnings = parse_csv(contents, encoding)
        else:
            warnings.append(f"Unknown extension .{ext} — attempting CSV parse")
            if is_large:
                df, parse_warnings, delimiter_used = parse_csv(contents, encoding, sample_only=True)
            else:
                df, parse_warnings = parse_csv(contents, encoding)
    except (pd.errors.ParserError, OSError, ValueError, UnicodeDecodeError, TypeError, KeyError, ImportError) as e:
        logger.warning("File parse failed for %s: %s: %s", filename, type(e).__name__, e)
        return {
            "success": False,
            "filename": filename,
            "error": str(e),
            "warnings": warnings,
        }

    warnings.extend(parse_warnings)

    # Build schema before any full-file patching. Large CSVs are sampled for
    # schema inference, then patched with chunked stats from the complete file.
    schema = build_column_schema(df)

    # For large CSVs, recompute accurate null/min/max/mean over the full file
    if is_large and ext in ("csv", "tsv", "txt", ""):
        try:
            all_cols = [c["name"] for c in schema]
            chunked_stats = _compute_stats_chunked(
                io.StringIO(contents.decode(encoding, errors="replace")),
                delimiter_used, encoding, all_cols
            )
            schema = _patch_schema_with_chunked_stats(schema, chunked_stats)
            # Get true row count from chunked stats
            true_rows = max(s["total"] for s in chunked_stats.values()) if chunked_stats else len(df)
        except (pd.errors.ParserError, OSError, ValueError, UnicodeDecodeError, TypeError, KeyError):
            logger.warning("Large-file chunked stats failed for %s", filename)
            true_rows = len(df)
    else:
        true_rows = len(df)

    # Header detection — only when user hasn't already specified a row
    header_suggestion = None
    raw_rows = []
    if header_row is None and ext in ("csv", "tsv", "txt", "xlsx", "xls"):
        try:
            raw_rows = get_raw_rows(contents, ext, encoding, n=8)
            detected, confidence = detect_header_row(contents, ext, encoding, df, max_scan=8)
            if detected is not None and detected > 0:
                preview = raw_rows[detected]["cells"][:6] if detected < len(raw_rows) else []
                header_suggestion = {
                    "suggested_row": int(detected),
                    "confidence": confidence,
                    "preview": preview,
                    "message": f"Row 1 may not be the real header. Row {detected} looks more like column names.",
                }
        except (pd.errors.ParserError, OSError, ValueError, UnicodeDecodeError, TypeError, KeyError) as exc:
            logger.warning("Header detection failed for %s: %s: %s", filename, type(exc).__name__, exc)

    # Sample rows — convert to JSON-safe types
    sample = df.head(SAMPLE_ROWS).copy()
    for col in sample.columns:
        if pd.api.types.is_datetime64_any_dtype(sample[col]):
            sample[col] = sample[col].astype(str)
        elif pd.api.types.is_float_dtype(sample[col]):
            sample[col] = sample[col].replace([float('inf'), float('-inf')], None)
    sample_rows = sample.where(pd.notna(sample), None).to_dict(orient="records")
    def _sanitize(v):
        if isinstance(v, float) and (v != v or v == float('inf') or v == float('-inf')):
            return None
        return v
    sample_rows = [{k: _sanitize(v) for k, v in row.items()} for row in sample_rows]

    # Will be called again after save_dataset assigns the id
    # We return a _df reference so store.py can persist it
    result = {
        "success": True,
        "filename": filename,
        "file_extension": ext,
        "header_row": header_row,
        "encoding": enc_info,
        "shape": {"rows": true_rows, "columns": len(df.columns)},
        "schema": schema,
        "sample_rows": sample_rows,
        "warnings": warnings,
        "header_suggestion": header_suggestion,
        "raw_rows": raw_rows,
        "_df": df,  # stripped before JSON response
    }
    return result
