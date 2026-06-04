import json
import uuid
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.services.object_storage import upload_dataset_artifact, delete_dataset_artifacts, download_dataset_artifact

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATASETS_DIR = DATA_DIR / "datasets"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)
_UNSET = object()
_COLLECTION = None
_MONGO_CHECKED = False


def _meta_path(dataset_id: str) -> Path:
    return DATASETS_DIR / f"{dataset_id}.json"

def _parquet_path(dataset_id: str) -> Path:
    return DATASETS_DIR / f"{dataset_id}.parquet"


def _mongo_uri() -> str | None:
    for key in ("MONGODB_URI", "MONGO_URI", "MONGO_URL", "MONGO_CONNECTION_STRING"):
        value = os.getenv(key)
        if value:
            return value
    return None


def _mongo_collection():
    global _COLLECTION, _MONGO_CHECKED
    if _MONGO_CHECKED:
        return _COLLECTION
    _MONGO_CHECKED = True
    uri = _mongo_uri()
    if not uri:
        return None
    try:
        from pymongo import MongoClient
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        db_name = (
            os.getenv("MONGODB_DB")
            or os.getenv("MONGO_DB")
            or os.getenv("MONGO_DATABASE")
            or os.getenv("DATABASE_NAME")
            or "dataflow"
        )
        collection_name = os.getenv("MONGODB_COLLECTION", "datasets")
        _COLLECTION = client[db_name][collection_name]
        _COLLECTION.create_index([("owner_id", 1), ("saved_at", -1)])
        _COLLECTION.create_index("expires_at")
    except Exception:
        _COLLECTION = None
    return _COLLECTION


def _mongo_doc(record: dict) -> dict:
    return {
        "_id": record["id"],
        "id": record["id"],
        "owner_id": record.get("owner_id"),
        "access": record.get("access", "anonymous"),
        "saved_at": record.get("saved_at"),
        "expires_at": record.get("expires_at"),
        "filename": record.get("filename"),
        "record_json": json.dumps(record, ensure_ascii=False),
    }


def _record_from_mongo(doc: dict) -> dict | None:
    try:
        return json.loads(doc.get("record_json") or "{}")
    except Exception:
        return None


def _read_local_record(dataset_id: str) -> dict | None:
    path = _meta_path(dataset_id)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_dataset_record(record: dict) -> dict:
    """Persist dataset metadata to MongoDB when configured, with local JSON as a cache/fallback."""
    with open(_meta_path(record["id"]), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    collection = _mongo_collection()
    if collection is not None:
        try:
            collection.replace_one({"_id": record["id"]}, _mongo_doc(record), upsert=True)
        except Exception:
            pass
    return record


def _anonymous_ttl_hours() -> int:
    try:
        return max(int(os.getenv("ANONYMOUS_DATASET_TTL_HOURS", "48")), 1)
    except Exception:
        return 48


def _parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _owned_by(data: dict, user_id: str | None) -> bool:
    owner = data.get("owner_id")
    if user_id:
        return owner == user_id
    return not owner


def save_dataset(parse_result: dict, owner_id: str | None = None) -> dict:
    dataset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    expires_at = None if owner_id else (datetime.now(timezone.utc) + timedelta(hours=_anonymous_ttl_hours())).isoformat()

    # Extract and save the dataframe separately
    df = parse_result.pop("_df", None)
    storage = {"backend": "local", "artifacts": []}
    if df is not None:
        try:
            parquet = _parquet_path(dataset_id)
            df.to_parquet(parquet, index=False)
            key = upload_dataset_artifact(dataset_id, parquet)
            storage["artifacts"].append({"kind": "active", "format": "parquet", "local": parquet.name, "r2_key": key})
            if key:
                storage["backend"] = "r2+local-cache"
        except Exception:
            # fallback: try saving as CSV if parquet fails
            try:
                csv_path = DATASETS_DIR / f"{dataset_id}.csv"
                df.to_csv(csv_path, index=False)
                key = upload_dataset_artifact(dataset_id, csv_path)
                storage["artifacts"].append({"kind": "active", "format": "csv", "local": csv_path.name, "r2_key": key})
                if key:
                    storage["backend"] = "r2+local-cache"
            except Exception:
                pass

    record = {
        "id": dataset_id,
        "saved_at": now,
        "owner_id": owner_id,
        "access": "user" if owner_id else "anonymous",
        "expires_at": expires_at,
        "storage": storage,
        **parse_result,
    }

    return save_dataset_record(record)


def cleanup_expired_datasets(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    deleted = 0
    seen = set()
    records = []
    collection = _mongo_collection()
    if collection is not None:
        try:
            for doc in collection.find({"access": "anonymous"}):
                data = _record_from_mongo(doc)
                if data:
                    records.append(data)
                    seen.add(data["id"])
        except Exception:
            pass
    for path in DATASETS_DIR.glob("*.json"):
        try:
            data = _read_local_record(path.stem)
            if data and data["id"] not in seen:
                records.append(data)
        except Exception:
            continue
    for data in records:
        try:
            expires = _parse_dt(data.get("expires_at"))
            if data.get("access") == "anonymous" and expires and expires <= now:
                if delete_dataset(data["id"]):
                    deleted += 1
        except Exception:
            continue
    return deleted


def list_datasets(user_id: str | None = None) -> list[dict]:
    cleanup_expired_datasets()
    records = []
    collection = _mongo_collection()
    if collection is not None:
        try:
            query = {"owner_id": user_id} if user_id else {"owner_id": None}
            for doc in collection.find(query).sort("saved_at", -1):
                data = _record_from_mongo(doc)
                if data:
                    records.append(data)
        except Exception:
            records = []
    else:
        for path in sorted(DATASETS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
            try:
                data = _read_local_record(path.stem)
                if data:
                    records.append(data)
            except Exception:
                continue
    summaries = []
    for data in records:
        try:
            if not _owned_by(data, user_id):
                continue
            summaries.append({
                "id": data["id"],
                "filename": data.get("filename"),
                "saved_at": data.get("saved_at"),
                "owner_id": data.get("owner_id"),
                "access": data.get("access", "anonymous"),
                "expires_at": data.get("expires_at"),
                "shape": data.get("shape"),
                "encoding": data.get("encoding"),
                "warnings": data.get("warnings", []),
            })
        except Exception:
            continue
    return summaries


def get_dataset(dataset_id: str, user_id: str | None | object = _UNSET) -> dict | None:
    data = None
    collection = _mongo_collection()
    if collection is not None:
        try:
            doc = collection.find_one({"_id": dataset_id})
            data = _record_from_mongo(doc) if doc else None
        except Exception:
            data = None
    if data is None:
        data = _read_local_record(dataset_id)
    if data is None:
        return None
    expires = _parse_dt(data.get("expires_at"))
    if data.get("access") == "anonymous" and expires and expires <= datetime.now(timezone.utc):
        delete_dataset(dataset_id)
        return None
    if user_id is not _UNSET and not _owned_by(data, user_id):
        return None
    return data


def delete_dataset(dataset_id: str, user_id: str | None = None) -> bool:
    data = get_dataset(dataset_id)
    if data is None:
        return False
    if not _owned_by(data, user_id):
        return False
    path = _meta_path(dataset_id)
    if path.exists():
        path.unlink()
    for p in DATASETS_DIR.glob(f"{dataset_id}*"):
        if p.is_file():
            p.unlink()
    collection = _mongo_collection()
    if collection is not None:
        try:
            collection.delete_one({"_id": dataset_id})
        except Exception:
            pass
    delete_dataset_artifacts(dataset_id)
    return True


def ensure_dataset_file(dataset_id: str, filename: str) -> Path | None:
    path = DATASETS_DIR / filename
    if path.exists():
        return path
    if download_dataset_artifact(dataset_id, filename, path):
        return path
    return None


def save_insight(
    dataset_id: str,
    insight: str,
    model: str,
    provider: str = "local",
    data_hash: str | None = None,
) -> None:
    """Add AI insight to an existing dataset record."""
    path = _meta_path(dataset_id)
    data = get_dataset(dataset_id)
    if not data:
        return
    data["insight"] = insight
    data["insight_model"] = model
    cache = data.setdefault("insight_cache", {})
    if data_hash:
        cache[f"{provider}:{model}:{data_hash}"] = {
            "insight": insight,
            "model": model,
            "provider": provider,
            "data_hash": data_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    save_dataset_record(data)


def get_cached_insight(
    dataset: dict,
    provider: str,
    model: str,
    data_hash: str,
) -> dict | None:
    cache = dataset.get("insight_cache", {})
    cached = cache.get(f"{provider}:{model}:{data_hash}")
    if not cached:
        return None
    return {
        "insight": cached.get("insight", ""),
        "model": cached.get("model", model),
        "cached": True,
    }
