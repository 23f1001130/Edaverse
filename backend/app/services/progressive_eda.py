"""Bounded-memory EDA: quick preview, mergeable full-data summaries, sampled views.

Counts spill to a temporary SQLite database rather than retaining unbounded sets
of categories in RAM. Completed summaries are revision-keyed and reusable in R2.
"""
import hashlib
from functools import partial
import json
import logging
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import uuid

import numpy as np
import pandas as pd

from app.services import eda
from app.services import object_storage

upload_dataset_artifact = partial(object_storage.upload_dataset_artifact, optional_cache=True)
download_dataset_artifact = partial(object_storage.download_dataset_artifact, optional_cache=True)

ENGINE_VERSION = 1
BATCH_ROWS = 10_000
SAMPLE_ROWS = 10_000
UPDATE_INTERVAL_SECONDS = 1.0
MAX_PAIR_COLUMNS = 40
CACHE_LIMIT_BYTES = 128 * 1024 * 1024
_WORKER = threading.BoundedSemaphore(1)
logger = logging.getLogger(__name__)


def revision_key(dataset):
    revision = dataset.get("data_revision") or {
        key: dataset.get(key) for key in ("saved_at", "shape", "schema", "workflow", "operations_log")
    }
    value = [ENGINE_VERSION, dataset["id"], dataset.get("owner_id"), revision,
             dataset.get("storage", {}).get("active_format"), SAMPLE_ROWS, MAX_PAIR_COLUMNS]
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:24]


def _cache_path(dataset):
    return eda.DATA_DIR / f'{dataset["id"]}.eda-{revision_key(dataset)}.eda-cache'


def _read_cache(dataset, remote=False):
    path = _cache_path(dataset)
    if remote and not path.exists():
        temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        try:
            if download_dataset_artifact(dataset["id"], path.name, temporary):
                temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    try:
        if path.stat().st_size > 8 * 1024 * 1024:
            return None
        result = json.loads(path.read_text(encoding="utf-8"))
        if result["analysis"].get("revision") != revision_key(dataset):
            return None
        if result["analysis"].get("status") != "complete":
            return None
        result["analysis"]["cached"] = True
        return result
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _save_cache(dataset, result):
    path = _cache_path(dataset)
    temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    try:
        text = json.dumps(result, allow_nan=False)
        if len(text.encode()) > 8 * 1024 * 1024:
            return
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
        upload_dataset_artifact(dataset["id"], path)
        # Only evict computed summaries; never dataset artifacts or metadata.
        files = sorted(eda.DATA_DIR.glob("*.eda-*.eda-cache"), key=lambda item: item.stat().st_mtime, reverse=True)
        size = 0
        for item in files:
            size += item.stat().st_size
            if size > CACHE_LIMIT_BYTES:
                item.unlink(missing_ok=True)
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("EDA cache save skipped: %s", type(exc).__name__)
    finally:
        temporary.unlink(missing_ok=True)


def _source_path(dataset):
    active = dataset.get("storage", {}).get("active_format", "parquet")
    for suffix in dict.fromkeys((active, "parquet", "csv")):
        path = eda.DATA_DIR / f'{dataset["id"]}.{suffix}'
        if path.exists():
            return path
        if eda.ensure_dataset_file(dataset["id"], path.name) and path.exists():
            return path
    raise FileNotFoundError("The saved dataset could not be loaded. Please retry.")


def iter_batches(path):
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq
        for batch in pq.ParquetFile(path).iter_batches(batch_size=BATCH_ROWS):
            yield batch.to_pandas()
    else:
        # Preserve category labels/IDs; numeric calculations explicitly coerce.
        with pd.read_csv(path, chunksize=BATCH_ROWS, dtype=str, on_bad_lines="error") as batches:
            yield from batches


class Reservoir:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.frame = pd.DataFrame()
        self.keys = np.array([], dtype=float)

    def add(self, frame):
        keys = np.concatenate((self.keys, self.rng.random(len(frame))))
        joined = pd.concat((self.frame, frame))
        keep = np.argpartition(keys, SAMPLE_ROWS - 1)[:SAMPLE_ROWS] if len(keys) > SAMPLE_ROWS else np.arange(len(keys))
        self.keys = keys[keep]
        self.frame = joined.iloc[keep]


class NumericSummary:
    def __init__(self, info):
        self.n = 0
        self.mean = self.m2 = self.m3 = 0.0
        self.minimum = math.inf
        self.maximum = -math.inf
        self.edges = None
        self.bins = np.zeros(20, dtype=np.int64)
        self.underflow = self.overflow = 0
        lo, hi = info.get("min"), info.get("max")
        if lo is not None and hi is not None and math.isfinite(lo) and math.isfinite(hi) and lo < hi:
            self.edges = np.linspace(lo, hi, 21)

    def add(self, values):
        values = values[np.isfinite(values)]
        n = len(values)
        if not n:
            return
        mean = float(values.mean())
        centered = values - mean
        m2 = float(np.dot(centered, centered))
        m3 = float(np.sum(centered ** 3))
        total = self.n + n
        delta = mean - self.mean
        self.m3 += m3 + delta ** 3 * self.n * n * (self.n - n) / total ** 2 + 3 * delta * (self.n * m2 - n * self.m2) / total
        self.m2 += m2 + delta ** 2 * self.n * n / total
        self.mean += delta * n / total
        self.n = total
        self.minimum = min(self.minimum, float(values.min()))
        self.maximum = max(self.maximum, float(values.max()))
        if self.edges is not None:
            self.bins += np.histogram(values, bins=self.edges)[0]
            self.underflow += int((values < self.edges[0]).sum())
            self.overflow += int((values > self.edges[-1]).sum())

    def stats(self):
        return {"min": eda._safe(np.float64(self.minimum)), "max": eda._safe(np.float64(self.maximum)),
                "mean": eda._safe(np.float64(self.mean)),
                "std": eda._safe(np.float64(math.sqrt(max(0.0, self.m2) / (self.n - 1)))) if self.n > 1 else None,
                "skewness": eda._safe(np.float64(self.n * math.sqrt(self.n - 1) / (self.n - 2) * self.m3 / self.m2 ** 1.5)) if self.n > 2 and self.m2 > 0 else 0.0}


class PairSummary:
    """Pairwise-complete Pearson sums, translated to avoid large-offset loss."""
    def __init__(self, columns):
        self.columns = columns
        shape = (len(columns), len(columns))
        self.count, self.sums, self.squares, self.products = (np.zeros(shape) for _ in range(4))
        self.origin = np.full(len(columns), np.nan)

    def add(self, frame):
        if not self.columns:
            return
        x = frame[self.columns].apply(lambda column: eda._numeric(column)).to_numpy(dtype=float)
        for index in range(len(self.columns)):
            valid = x[:, index][np.isfinite(x[:, index])]
            if np.isnan(self.origin[index]) and len(valid):
                self.origin[index] = valid[0]
        mask = np.isfinite(x).astype(float)
        values = np.where(mask, x - np.nan_to_num(self.origin), 0.0)
        self.count += mask.T @ mask
        self.sums += values.T @ mask
        self.squares += (values * values).T @ mask
        self.products += values.T @ values

    def result(self):
        if len(self.columns) < 2:
            return None
        with np.errstate(divide="ignore", invalid="ignore"):
            covariance = self.products - self.sums * self.sums.T / self.count
            variance = np.maximum(0, self.squares - self.sums ** 2 / self.count)
            correlation = covariance / np.sqrt(variance * variance.T)
        usable = [i for i in range(len(self.columns)) if variance[i, i] > 0]
        if len(usable) < 2:
            return None
        return {"method": "pearson", "columns": [self.columns[i] for i in usable],
                "matrix": [{"x": self.columns[i], "y": self.columns[j],
                            "value": eda._safe(float(np.clip(correlation[i, j], -1, 1))) if self.count[i, j] >= 2 else None}
                           for i in usable for j in usable]}


class FullSummary:
    def __init__(self, schema, connection):
        self.schema = schema
        self.db = connection
        self.db.execute("PRAGMA cache_size=-4096")
        self.db.execute("PRAGMA temp_store=FILE")
        self.db.execute("CREATE TABLE counts (col TEXT, value TEXT, n INTEGER, PRIMARY KEY(col,value)) WITHOUT ROWID")
        self.numeric = {c["name"]: NumericSummary(c) for c in schema if c["type"] in ("integer", "float")}
        self.categories = [c["name"] for c in schema if c["type"] in ("categorical", "boolean", "text", "empty")]
        self.times = [c["name"] for c in schema if c["type"] == "datetime"]
        self.time_bounds = {}
        self.nulls = {c["name"]: 0 for c in schema}
        self.rows = 0
        self.pairs = PairSummary(list(self.numeric)[:MAX_PAIR_COLUMNS])
        self.missing_columns = list(self.nulls)[:MAX_PAIR_COLUMNS]
        self.missing_pairs = np.zeros((len(self.missing_columns), len(self.missing_columns)), dtype=np.int64)

    def add(self, frame):
        self.rows += len(frame)
        for name in self.nulls:
            self.nulls[name] += int(frame[name].isna().sum())
        for name, summary in self.numeric.items():
            summary.add(eda._numeric(frame[name]).to_numpy(dtype=float))
        for name in self.categories:
            self._count(name, frame[name].dropna().astype(str).value_counts())
        for name in self.times:
            dates = pd.to_datetime(frame[name], errors="coerce", format="mixed", utc=True).dropna()
            if len(dates):
                self._count(name, dates.dt.strftime("%Y-%m").value_counts())
                lo, hi = self.time_bounds.get(name, (dates.min(), dates.max()))
                self.time_bounds[name] = min(lo, dates.min()), max(hi, dates.max())
        self.db.commit()
        self.pairs.add(frame)
        missing = frame[self.missing_columns].isna().to_numpy(dtype=np.int64)
        self.missing_pairs += missing.T @ missing

    def _count(self, column, counts):
        self.db.executemany("INSERT INTO counts VALUES (?,?,?) ON CONFLICT(col,value) DO UPDATE SET n=n+excluded.n",
                            ((column, str(value), int(count)) for value, count in counts.items()))

    def category(self, name):
        unique, total = self.db.execute("SELECT count(*),coalesce(sum(n),0) FROM counts WHERE col=?", (name,)).fetchone()
        values = [{"value": value, "count": count} for value, count in self.db.execute(
            "SELECT value,n FROM counts WHERE col=? ORDER BY n DESC,value LIMIT 10", (name,))]
        return unique, total, values

    def missingness(self):
        columns = [name for name in self.missing_columns if self.nulls[name] > 0]
        if len(columns) < 2:
            return None
        indices = {name: self.missing_columns.index(name) for name in columns}
        matrix, flags = [], []
        for a in columns:
            for b in columns:
                both = int(self.missing_pairs[indices[a], indices[b]])
                actual = both / self.rows
                expected = self.nulls[a] * self.nulls[b] / self.rows ** 2
                matrix.append({"x": a, "y": b, "both_missing": both, "pct": round(actual * 100, 1)})
                if a < b and expected > 0 and actual / expected > 2 and actual > 0.02:
                    flags.append({"a": a, "b": b, "actual_pct": round(actual * 100, 1), "expected_pct": round(expected * 100, 1), "lift": round(actual / expected, 1)})
        return {"columns": columns, "matrix": matrix, "flagged_pairs": sorted(flags, key=lambda item: item["lift"], reverse=True)[:5]}

    def distributions(self, sampled):
        lookup = {item["column"]: item for item in sampled}
        results = []
        for info in self.schema:
            name, kind = info["name"], info["type"]
            if name in self.numeric:
                summary = self.numeric[name]
                if not summary.n or summary.edges is None:
                    continue
                sample = lookup.get(name, {})
                bins = [{"range": f"{summary.edges[i]:.4g}–{summary.edges[i+1]:.4g}", "count": int(count)} for i, count in enumerate(summary.bins)]
                if summary.underflow:
                    bins.insert(0, {"range": f"Below {summary.edges[0]:.4g}", "count": summary.underflow})
                if summary.overflow:
                    bins.append({"range": f"Above {summary.edges[-1]:.4g}", "count": summary.overflow})
                results.append({"column": name, "type": "histogram", "col_type": kind,
                    "bins": bins,
                    "stats": {**sample.get("stats", {}), **summary.stats()},
                    "boxplot": sample.get("boxplot"), "quantiles_sampled": True, "scope": "all_processed_rows"})
            elif name in self.categories:
                unique, total, values = self.category(name)
                id_like = unique / max(total, 1) > .95 and (kind in ("text", "categorical") or any(signal in name.lower() for signal in ("id", "uuid", "key", "code", "number", "ref")))
                if id_like:
                    results.append({"column": name, "type": "skipped", "col_type": kind, "reason": "Unique identifier — no distribution to show", "unique": unique})
                elif values:
                    results.append({"column": name, "type": "barchart", "col_type": kind,
                        "values": values, "total_unique": unique, "other_count": total - sum(v["count"] for v in values),
                        "scope": "all_processed_rows", "cat_stats": {"unique": unique, "top": values[0]["value"], "freq": values[0]["count"], "freq_pct": round(values[0]["count"] / total * 100, 1), "count": total}})
            elif name in self.time_bounds:
                timeline = [{"period": period, "count": n} for period, n in self.db.execute("SELECT value,n FROM counts WHERE col=? ORDER BY value", (name,))]
                lo, hi = self.time_bounds[name]
                results.append({"column": name, "type": "timeline", "col_type": kind, "timeline": timeline,
                    "min": str(lo), "max": str(hi), "count": sum(value["count"] for value in timeline), "scope": "all_processed_rows"})
        return results


def _event(stage, label, progress, data=None):
    result = {"stage": stage, "label": label, "progress": progress}
    if data is not None:
        result["data"] = data
    return result


def _snapshot(dataset, full, reservoir, final=False):
    from app.services.parser import build_column_schema
    frame = reservoir.frame.copy()
    for info in full.schema:
        name = info["name"]
        if name in full.numeric:
            frame[name] = eda._numeric(frame[name])
        elif name in full.times:
            frame[name] = pd.to_datetime(frame[name], errors="coerce", format="mixed", utc=True)
    schema = build_column_schema(frame)
    sampled = full.rows > len(frame)
    analysis = {"status": "complete" if final else "processing", "rows": full.rows, "processed_rows": full.rows,
                "total_rows": dataset.get("shape", {}).get("rows", full.rows), "sampled": sampled,
                "sample_rows": len(frame), "sample_method": "uniform_reservoir", "revision": revision_key(dataset),
                "pair_column_limit": MAX_PAIR_COLUMNS,
                "pair_columns_limited": len(full.numeric) > MAX_PAIR_COLUMNS or len(full.schema) > MAX_PAIR_COLUMNS,
                "full_metrics": ["histograms", "category_counts", "timelines", "numeric_moments", "pearson", "nulls", "missingness"],
                "sampled_metrics": ["quantiles", "boxplots", "outliers", "spearman", "scatter", "pca", "pivot_heatmap", "numeric_profile", "observations", "missingness_matrix"],
                "cached": False}
    result = eda.compute_eda_frame(dataset, frame, schema, analysis)
    result["distributions"] = full.distributions(result["distributions"])
    for distribution in result["distributions"]:
        if distribution.get("quantiles_sampled"):
            distribution["sample_rows"] = len(frame)
    if result["correlation_spearman"]:
        result["correlation_spearman"].update(scope="sample", sample_rows=len(frame))
    result["correlation"] = full.pairs.result()
    result["missingness"] = full.missingness()
    result["nulls"] = [{"column": name, "null_count": count, "null_pct": round(count / full.rows * 100, 1), "total": full.rows} for name, count in full.nulls.items()]
    full_schema = [{**info, "null_count": full.nulls[info["name"]],
                    "null_pct": round(full.nulls[info["name"]] / full.rows * 100, 1),
                    **(full.numeric[info["name"]].stats() if info["name"] in full.numeric else {})}
                   for info in schema]
    result["observations"] = eda.compute_observations(frame, full_schema, result["correlation"], result["outliers"], sampled=sampled)
    for column in result["numeric_profile"]["columns"]:
        if column["column"] in full.numeric:
            column.update(full.numeric[column["column"]].stats())
            column["abs_skewness"] = abs(column["skewness"]) if column["skewness"] is not None else None
            column["null_pct"] = round(full.nulls[column["column"]] / full.rows * 100, 1)
    result["numeric_profile"]["skewed_count"] = sum((column["abs_skewness"] or 0) > 1 for column in result["numeric_profile"]["columns"])
    # Categorical triage uses the same complete counts as its bar charts.
    for column in result["categorical_profile"]["columns"]:
        unique, count, values = full.category(column["column"])
        top = values[0] if values else {"value": None, "count": 0}
        ratio = unique / max(count, 1)
        strategy = "identifier" if ratio > .95 else "one-hot" if unique <= 10 else "ordinal/frequency" if unique <= 50 else "high-cardinality"
        column.update(unique=unique, count=count, top=top["value"], freq_pct=round(top["count"] / max(count, 1) * 100, 1),
                      null_pct=round(full.nulls[column["column"]] / full.rows * 100, 1), cardinality_ratio=round(ratio * 100, 1), strategy=strategy,
                      is_imbalanced=unique > 1 and top["count"] / max(count, 1) >= .95)
    categories = result["categorical_profile"]
    categories["high_cardinality_count"] = sum(column["strategy"] in ("identifier", "high-cardinality") for column in categories["columns"])
    categories["imbalanced_count"] = sum(column["is_imbalanced"] for column in categories["columns"])
    return result


def stream_analysis(dataset, timeout=None):
    """Each partial event is cumulative; only a verified final result is cached."""
    deadline = time.monotonic() + (timeout or int(os.getenv("EDA_STREAM_TIMEOUT_SECS", "300")))

    def check():
        if time.monotonic() > deadline:
            raise TimeoutError("Full analysis took too long. Your preview is available; retry to finish.")

    cached = _read_cache(dataset)
    if cached:
        yield _event("complete", "Full analysis ready", 1, cached)
        return
    yield _event("loading", "Loading a quick preview…", .01)
    cached = _read_cache(dataset, remote=True)
    if cached:
        yield _event("complete", "Full analysis ready", 1, cached)
        return
    frame, schema, old_scope = eda.prepare_eda_frame(dataset)
    if frame.empty:
        raise ValueError("No data available for EDA")
    scope = {**old_scope, "status": "preview", "processed_rows": len(frame), "sample_rows": len(frame), "sample_method": "first_rows"}
    preview = eda.compute_eda_frame(dataset, frame, schema, scope)
    if not old_scope["sampled"]:
        preview["analysis"].update(status="complete", revision=revision_key(dataset), cached=False)
        _save_cache(dataset, preview)
        yield _event("complete", "Full analysis ready", 1, preview)
        return
    yield _event("preview", f"Preview ready — {len(frame):,} rows", .03, preview)
    del frame, preview

    while not _WORKER.acquire(timeout=.25):
        check()
        cached = _read_cache(dataset)
        if cached:
            yield _event("complete", "Full analysis ready", 1, cached)
            return
        yield _event("queued", "Preview ready — waiting to analyze all rows…", .03)
    try:
        cached = _read_cache(dataset)
        if cached:
            yield _event("complete", "Full analysis ready", 1, cached)
            return
        path = _source_path(dataset)
        original_stat = path.stat()
        seed = int(revision_key(dataset)[:16], 16)
        reservoir = Reservoir(seed)
        with tempfile.TemporaryDirectory(prefix=f'{dataset["id"]}.eda-work-', dir=eda.DATA_DIR) as directory:
            # Starlette may resume a synchronous stream on a different worker
            # thread after each yield. Access stays serial within this generator.
            connection = sqlite3.connect(Path(directory) / "counts.sqlite", check_same_thread=False)
            try:
                full = FullSummary(dataset["schema"], connection)
                last_update = time.monotonic()
                for batch in iter_batches(path):
                    check()
                    batch.index = range(full.rows, full.rows + len(batch))
                    full.add(batch)
                    reservoir.add(batch)
                    if time.monotonic() - last_update >= UPDATE_INTERVAL_SECONDS:
                        total = dataset.get("shape", {}).get("rows", full.rows)
                        result = _snapshot(dataset, full, reservoir)
                        yield _event("batch", f"Analyzed {full.rows:,} / {total:,} rows", min(.9, .05 + .85 * full.rows / max(total, 1)), result)
                        last_update = time.monotonic()
                expected = dataset.get("shape", {}).get("rows", full.rows)
                if full.rows != expected:
                    raise ValueError("The saved row count changed. Refresh the dataset and retry analysis.")
                # If metadata min/max were rounded or changed, recompute histogram
                # edges from the actual full scan and count again in bounded batches.
                recount = {name: summary for name, summary in full.numeric.items()
                           if summary.n and (summary.edges is None or int(summary.bins.sum()) != summary.n)}
                if recount:
                    yield _event("finalizing", "Finalizing full-data histogram ranges…", .92)
                    for summary in recount.values():
                        summary.edges = np.histogram_bin_edges([summary.minimum, summary.maximum], bins=20)
                        summary.bins[:] = 0
                        summary.underflow = summary.overflow = 0
                    for batch in iter_batches(path):
                        check()
                        for name, summary in recount.items():
                            values = eda._numeric(batch[name], dropna=True).to_numpy(dtype=float)
                            summary.bins += np.histogram(values, bins=summary.edges)[0]
                check()
                current_stat = path.stat()
                if (original_stat.st_size, original_stat.st_mtime_ns) != (current_stat.st_size, current_stat.st_mtime_ns):
                    raise ValueError("The dataset changed during analysis. Retry to analyze the latest version.")
                result = _snapshot(dataset, full, reservoir, final=True)
            finally:
                connection.close()
        _save_cache(dataset, result)
        yield _event("complete", "Full dataset analyzed", 1, result)
    finally:
        _WORKER.release()
