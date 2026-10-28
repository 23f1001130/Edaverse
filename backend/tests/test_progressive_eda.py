import json
import uuid

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.services import eda, parser, store, progressive_eda as progressive
from app.main import app


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(eda, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store, "DATASETS_DIR", tmp_path)
    monkeypatch.setattr(store, "_MONGO_CHECKED", True)
    monkeypatch.setattr(store, "_COLLECTION", None)
    monkeypatch.setattr(progressive, "download_dataset_artifact", lambda *args: False)
    monkeypatch.setattr(progressive, "upload_dataset_artifact", lambda *args: None)
    monkeypatch.setattr(progressive, "UPDATE_INTERVAL_SECONDS", 0)
    return tmp_path


def dataset(storage, rows=20_007, format="csv"):
    rng = np.random.default_rng(17)
    x = rng.normal(size=rows)
    x[10_000:] += 100  # Distribution changes completely after the old cutoff.
    y = x * 3 + rng.normal(size=rows)
    x[::11] = np.nan
    y[::13] = np.nan
    frame = pd.DataFrame({"amount": x, "spend": y,
        "group": ["early"] * min(10_000, rows) + ["late"] * max(0, rows - 10_000),
        "date": pd.date_range("2024-01-01", periods=rows, freq="h")})
    record = {"id": str(uuid.uuid4()), "data_revision": str(uuid.uuid4()),
              "filename": "late-patterns.csv", "schema": parser.build_column_schema(frame.head(10_000)),
              "shape": {"rows": rows, "columns": len(frame.columns)}, "storage": {"active_format": format}}
    path = storage / f'{record["id"]}.{format}'
    frame.to_csv(path, index=False) if format == "csv" else frame.to_parquet(path, index=False)
    return record, frame


@pytest.mark.parametrize("format", ["csv", "parquet"])
def test_preview_then_cumulative_batches_include_late_rows(storage, format):
    record, frame = dataset(storage, format=format)
    events = list(progressive.stream_analysis(record))
    assert events[1]["stage"] == "preview"
    assert events[1]["data"]["analysis"]["rows"] == 10_000
    batches = [event["data"] for event in events if event["stage"] == "batch"]
    assert [batch["analysis"]["processed_rows"] for batch in batches] == [10_000, 20_000, len(frame)]
    for batch in batches:
        group = next(chart for chart in batch["distributions"] if chart["column"] == "group")
        assert sum(value["count"] for value in group["values"]) == batch["analysis"]["processed_rows"]
    result = events[-1]["data"]
    assert events[-1]["stage"] == "complete"
    assert result["analysis"]["status"] == "complete"
    assert result["analysis"]["rows"] == len(frame)
    assert result["analysis"]["sample_rows"] == 10_000
    amount = next(chart for chart in result["distributions"] if chart["column"] == "amount")
    assert sum(bin["count"] for bin in amount["bins"]) == int(frame.amount.notna().sum())
    assert amount["stats"]["mean"] == pytest.approx(frame.amount.mean(), abs=0.0001)
    assert amount["stats"]["std"] == pytest.approx(frame.amount.std(), abs=0.0001)
    assert amount["stats"]["skewness"] == pytest.approx(frame.amount.skew(), abs=0.0001)
    assert amount["quantiles_sampled"]
    pair = next(cell for cell in result["correlation"]["matrix"] if cell["x"] == "amount" and cell["y"] == "spend")
    assert pair["value"] == pytest.approx(frame[["amount", "spend"]].corr().iloc[0, 1], abs=0.0001)
    both = next(cell for cell in result["missingness"]["matrix"] if cell["x"] == "amount" and cell["y"] == "spend")
    assert both["both_missing"] == int((frame.amount.isna() & frame.spend.isna()).sum())
    timeline = next(chart for chart in result["distributions"] if chart["column"] == "date")
    assert sum(period["count"] for period in timeline["timeline"]) == len(frame)
    json.dumps(result, allow_nan=False)


def test_pairwise_missing_values_and_large_offsets_match_pandas():
    rng = np.random.default_rng(3)
    frame = pd.DataFrame({"a": 1e12 + rng.normal(size=5000), "b": 2e12 + rng.normal(size=5000)})
    frame.loc[::7, "a"] = np.nan
    frame.loc[::9, "b"] = np.nan
    summary = progressive.PairSummary(list(frame.columns))
    for start in range(0, len(frame), 1000):
        summary.add(frame.iloc[start:start + 1000])
    value = next(cell["value"] for cell in summary.result()["matrix"] if cell["x"] == "a" and cell["y"] == "b")
    assert value == pytest.approx(frame.corr().iloc[0, 1], abs=0.0002)


def test_complete_cache_reuses_result_and_new_revision_recomputes(storage, monkeypatch):
    record, _ = dataset(storage, rows=10_007)
    first = list(progressive.stream_analysis(record))[-1]["data"]
    original = progressive.iter_batches
    monkeypatch.setattr(progressive, "iter_batches", lambda *args: pytest.fail("Cached analysis must not rescan data"))
    second = list(progressive.stream_analysis(record))
    assert len(second) == 1 and second[0]["stage"] == "complete"
    assert second[0]["data"]["analysis"]["cached"]
    assert second[0]["data"]["distributions"] == first["distributions"]
    monkeypatch.setattr(progressive, "iter_batches", original)
    record["data_revision"] = str(uuid.uuid4())
    third = list(progressive.stream_analysis(record))
    assert third[1]["stage"] == "preview"
    assert not third[-1]["data"]["analysis"]["cached"]
    assert third[-1]["data"]["analysis"]["revision"] != first["analysis"]["revision"]


def test_preview_respects_active_csv_even_when_an_older_parquet_exists(storage):
    record, frame = dataset(storage, rows=10_007)
    pd.DataFrame({"stale": [999]}).to_parquet(storage / f'{record["id"]}.parquet', index=False)
    preview, _, _ = eda.prepare_eda_frame(record)
    assert list(preview.columns) == list(frame.columns)


def test_cloud_cache_survives_local_cache_loss(storage, monkeypatch):
    cloud = {}
    monkeypatch.setattr(progressive, "upload_dataset_artifact", lambda dataset_id, path: cloud.update({path.name: path.read_bytes()}))
    record, _ = dataset(storage, rows=10_007)
    list(progressive.stream_analysis(record))
    progressive._cache_path(record).unlink()

    def restore(dataset_id, filename, path):
        path.write_bytes(cloud[filename])
        return True

    monkeypatch.setattr(progressive, "download_dataset_artifact", restore)
    monkeypatch.setattr(progressive, "iter_batches", lambda *args: pytest.fail("Remote cache must avoid a full scan"))
    monkeypatch.setattr(eda, "prepare_eda_frame", lambda *args: pytest.fail("Remote cache must avoid restoring the full source just for a preview"))
    final = list(progressive.stream_analysis(record))[-1]
    assert final["stage"] == "complete" and final["data"]["analysis"]["cached"]


def test_cancelling_analysis_cleans_scratch_and_releases_worker(storage):
    record, _ = dataset(storage)
    stream = progressive.stream_analysis(record)
    assert next(stream)["stage"] == "loading"
    assert next(stream)["stage"] == "preview"
    assert next(stream)["stage"] == "batch"
    stream.close()
    assert not list(storage.glob("*.eda-work-*"))
    assert not progressive._cache_path(record).exists()
    assert progressive._WORKER.acquire(blocking=False)
    progressive._WORKER.release()


def test_deadline_preserves_preview_and_never_caches_partial_results(storage):
    record, _ = dataset(storage)
    stream = progressive.stream_analysis(record, timeout=0.000001)
    assert next(stream)["stage"] == "loading"
    assert next(stream)["stage"] == "preview"
    with pytest.raises(TimeoutError):
        next(stream)
    assert not progressive._cache_path(record).exists()


def test_authorized_http_stream_reaches_completion_and_reuses_cache(storage, monkeypatch):
    import app.routers.eda as route
    record, frame = dataset(storage, rows=10_007)
    record["owner_id"] = "owner-alice"
    store.save_dataset_record(record)
    monkeypatch.setattr(route, "get_request_user_id", lambda request: "owner-alice")
    with TestClient(app) as client:
        response = client.get(f'/api/datasets/{record["id"]}/eda/stream')
        assert response.status_code == 200
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        assert any(event["stage"] == "preview" for event in events)
        assert events[-1]["stage"] == "complete"
        assert events[-1]["data"]["analysis"]["rows"] == len(frame)
        cached = client.get(f'/api/datasets/{record["id"]}/eda')
        assert cached.status_code == 200 and cached.json()["analysis"]["cached"]


def test_duplicate_stream_waits_and_reuses_first_result(storage):
    record, _ = dataset(storage, rows=10_007)
    first, second = progressive.stream_analysis(record), progressive.stream_analysis(record)
    next(first)
    next(first)
    assert next(first)["stage"] == "batch"  # Holds the single analysis slot.
    next(second)
    next(second)
    assert next(second)["stage"] == "queued"
    assert list(first)[-1]["stage"] == "complete"
    tail = list(second)
    assert tail[-1]["data"]["analysis"]["cached"]


@pytest.mark.parametrize("suffix", ["eda", "eda/stream", "report", "target-analysis?target=amount", "target-analysis/stream?target=amount", "model-importance?target=amount", "comparison"])
def test_analysis_endpoints_check_owner_before_computing_or_reading_cache(storage, suffix):
    record, _ = dataset(storage, rows=10_007)
    record["owner_id"] = "owner-alice"
    store.save_dataset_record(record)
    with TestClient(app) as client:
        response = client.get(f'/api/datasets/{record["id"]}/{suffix}')
    assert response.status_code == 404
    assert not progressive._cache_path(record).exists()
