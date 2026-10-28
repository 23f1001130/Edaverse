import io
import asyncio
import json
import sys
from pathlib import Path

import pandas as pd
import pytest
import httpx
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import parser, store, eda
from app.main import app


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(parser, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store, "DATASETS_DIR", tmp_path)
    monkeypatch.setattr(eda, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store, "_MONGO_CHECKED", True)
    monkeypatch.setattr(store, "_COLLECTION", None)
    monkeypatch.setattr(store, "upload_dataset_artifact", lambda *args: None)
    monkeypatch.setattr(parser, "SMALL_FILE_THRESHOLD", 1)
    return tmp_path


def test_streamed_csv_retains_tail_and_exact_missing_counts(isolated_storage, monkeypatch):
    # The tail differs from the initial 10,000-row profile; it must survive storage.
    content = b"id,value,label\n" + b"1,10,normal\n" * 10001 + b"2,,tail\n"
    result = parser.parse_upload("large.csv", io.BytesIO(content), len(content))
    assert result["shape"]["rows"] == 10002
    assert result["schema"][1]["null_count"] == 1
    saved = store.save_dataset(result)
    assert "_data_path" not in saved and "_df" not in saved
    json.dumps(saved)
    persisted = pd.read_csv(isolated_storage / f'{saved["id"]}.csv')
    assert len(persisted) == 10002
    assert persisted.iloc[-1]["label"] == "tail"
    def unexpected_download(*args):
        pytest.fail("An available local dataset must not trigger an R2 lookup")
    monkeypatch.setattr(eda, "ensure_dataset_file", unexpected_download)
    frame, schema, scope = eda.prepare_eda_frame(saved)
    assert len(frame) == 10000
    assert scope == {"sampled": True, "rows": 10000, "total_rows": 10002}
    nulls = eda.compute_nulls(frame, saved["schema"], 10002)
    assert nulls[1]["null_count"] == 1
    assert nulls[1]["total"] == 10002


def test_streamed_tsv_reparse_respects_header_and_preserves_values(isolated_storage):
    content = b"export\tmetadata\ncode\tname\n001\tAlice\n002\tBob\n"
    result = parser.parse_upload("data.tsv", io.BytesIO(content), len(content), header_row=1)
    persisted = pd.read_csv(result["_data_path"], dtype=str)
    assert list(persisted.columns) == ["code", "name"]
    assert persisted["code"].tolist() == ["001", "002"]
    assert result["shape"]["rows"] == 2


@pytest.mark.parametrize("reader", ["openpyxl", "calamine"])
def test_streamed_excel_retains_all_rows_and_header_selection(isolated_storage, monkeypatch, reader):
    monkeypatch.setenv("XLSX_READER", reader)
    from openpyxl import Workbook
    source = io.BytesIO()
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet()
    sheet.append(["export", None])
    sheet.append(["code", "value"])
    for index in range(10005):
        sheet.append([f"{index:06}", index if index != 10004 else None])
    workbook.save(source)
    result = parser.parse_upload("retail.xlsx", source, source.tell(), header_row=1)
    assert result["shape"] == {"rows": 10005, "columns": 2}
    assert result["profile"]["reader"] == reader
    assert result["schema"][1]["null_count"] == 1
    persisted = pd.read_csv(result["_data_path"], dtype=str)
    assert persisted.iloc[-1]["code"] == "010004"


def test_bad_large_csv_cleans_temporary_file(isolated_storage):
    content = b'a,b\n1,2\n3,4,5\n'
    with pytest.raises(pd.errors.ParserError):
        parser.parse_upload("broken.csv", io.BytesIO(content), len(content))
    assert list(isolated_storage.iterdir()) == []


def test_upload_limits_and_clear_parse_error(isolated_storage, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    with TestClient(app) as client:
        response = client.post("/api/upload", files={"file": ("big.csv", b"x" * (1024 * 1024 + 1))})
        assert response.status_code == 413
        response = client.post("/api/upload", files={"file": ("broken.csv", b'a,b\n1,2\n3,4,5\n')})
        assert response.status_code == 400
        assert "Could not read" in response.json()["detail"]


def test_signed_in_identity_is_verified_before_parsing_and_retained_after_token_expires(isolated_storage, monkeypatch):
    import app.routers.upload as route
    parsed = False
    checks = []
    original_parse = route.parse_upload

    def identity(request):
        checks.append(parsed)
        return None if parsed else "owner-alice"

    def slow_parse(*args):
        nonlocal parsed
        result = original_parse(*args)
        parsed = True  # The submitted short-lived JWT would now be expired.
        return result

    monkeypatch.setattr(route, "get_request_user_id", identity)
    monkeypatch.setattr(route, "parse_upload", slow_parse)
    with TestClient(app) as client:
        response = client.post("/api/upload", files={"file": ("data.csv", b"value\n1\n2\n")}, headers={"Authorization": "Bearer valid-at-start"})
    assert response.status_code == 200
    assert response.json()["owner_id"] == "owner-alice"
    assert response.json()["access"] == "user"
    assert response.json()["expires_at"] is None
    assert checks == [False]


def test_invalid_upload_credentials_do_not_silently_create_guest_data(isolated_storage, monkeypatch):
    import app.routers.upload as route
    monkeypatch.setattr(route, "get_request_user_id", lambda request: None)
    monkeypatch.setattr(route, "parse_upload", lambda *args: pytest.fail("Invalid identity must stop before parsing"))
    with TestClient(app) as client:
        response = client.post("/api/upload", files={"file": ("data.csv", b"value\n1\n")}, headers={"Authorization": "Bearer expired"})
    assert response.status_code == 401
    assert "could not be verified" in response.json()["detail"]
    assert not list(isolated_storage.iterdir())


def test_upload_authenticates_before_receiving_slow_multipart_body(isolated_storage, monkeypatch):
    import app.routers.upload as route
    body_started = False
    checks = []

    def identity(request):
        checks.append(body_started)
        # Model a token valid at request start, expired by the end of transfer.
        return None if body_started else 'owner-slow-upload'

    monkeypatch.setattr(route, 'get_request_user_id', identity)

    async def run():
        multipart = httpx.Request('POST', 'http://test/api/upload', files={'file': ('data.csv', b'value\n1\n2\n')})
        body = multipart.read()

        async def slow_body():
            nonlocal body_started
            assert checks == [False], 'Identity must be verified before the first file bytes are read'
            body_started = True
            yield body[:len(body) // 2]
            await asyncio.sleep(0)
            yield body[len(body) // 2:]

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            return await client.post('/api/upload', content=slow_body(), headers={
                'Content-Type': multipart.headers['Content-Type'], 'Authorization': 'Bearer valid-at-request-start',
            })

    response = asyncio.run(run())
    assert response.status_code == 200, response.text
    assert response.json()['owner_id'] == 'owner-slow-upload'
    assert response.json()['access'] == 'user'
    assert checks == [False]


def test_invalid_upload_auth_is_rejected_without_reading_file_bytes(monkeypatch):
    import app.routers.upload as route
    monkeypatch.setattr(route, 'get_request_user_id', lambda request: None)
    messages = []

    async def unexpected_receive():
        pytest.fail('Invalid credentials must be rejected before reading the request body')

    async def unexpected_app(*args):
        pytest.fail('Invalid credentials must not reach multipart parsing')

    async def send(message):
        messages.append(message)

    scope = {'type': 'http', 'method': 'POST', 'path': '/api/upload', 'headers': [(b'authorization', b'Bearer invalid')]}
    asyncio.run(route.UploadAuthenticationMiddleware(unexpected_app)(scope, unexpected_receive, send))
    assert messages[0]['status'] == 401


def test_processing_keeps_config_responsive_and_rejects_overlapping_uploads(isolated_storage, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import app.routers.upload as route
    entered, release = Event(), Event()

    def slow_parse(*args):
        entered.set()
        assert release.wait(5)
        return {"success": False, "error": "test"}

    monkeypatch.setattr(route, "parse_upload", slow_parse)
    with TestClient(app) as client, ThreadPoolExecutor() as executor:
        pending = executor.submit(client.post, "/api/upload", files={"file": ("one.csv", b"a\n1")})
        assert entered.wait(5)
        try:
            assert client.get("/api/config").status_code == 200
            busy = client.post("/api/upload", files={"file": ("two.csv", b"a\n2")})
            assert busy.status_code == 503
        finally:
            release.set()
        assert pending.result().status_code == 200


def test_promoted_parquet_is_restored_instead_of_original_csv(isolated_storage, monkeypatch):
    from app.routers.cleaning import _refresh_schema_in_store
    content = b"value\n1\n2\n"
    saved = store.save_dataset(parser.parse_upload("data.csv", io.BytesIO(content), len(content)))
    changed = pd.DataFrame({"value": [99, 100]})
    updated = _refresh_schema_in_store(saved["id"], changed)
    assert updated["storage"]["active_format"] == "parquet"

    def restore(dataset_id, filename):
        assert filename == f"{dataset_id}.parquet"
        changed.to_parquet(isolated_storage / filename, index=False)

    monkeypatch.setattr(eda, "ensure_dataset_file", restore)
    assert eda._load_df(updated)["value"].tolist() == [99, 100]
