import json
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATASETS_DIR = DATA_DIR / "datasets"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def _meta_path(dataset_id: str) -> Path:
    return DATASETS_DIR / f"{dataset_id}.json"

def _parquet_path(dataset_id: str) -> Path:
    return DATASETS_DIR / f"{dataset_id}.parquet"


def save_dataset(parse_result: dict) -> dict:
    dataset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Extract and save the dataframe separately
    df = parse_result.pop("_df", None)
    if df is not None:
        try:
            df.to_parquet(_parquet_path(dataset_id), index=False)
        except Exception:
            # fallback: try saving as CSV if parquet fails
            try:
                df.to_csv(DATASETS_DIR / f"{dataset_id}.csv", index=False)
            except Exception:
                pass

    record = {
        "id": dataset_id,
        "saved_at": now,
        **parse_result,
    }

    with open(_meta_path(dataset_id), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return record


def list_datasets() -> list[dict]:
    summaries = []
    for path in sorted(DATASETS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            summaries.append({
                "id": data["id"],
                "filename": data.get("filename"),
                "saved_at": data.get("saved_at"),
                "shape": data.get("shape"),
                "encoding": data.get("encoding"),
                "warnings": data.get("warnings", []),
            })
        except Exception:
            continue
    return summaries


def get_dataset(dataset_id: str) -> dict | None:
    path = _meta_path(dataset_id)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def delete_dataset(dataset_id: str) -> bool:
    path = _meta_path(dataset_id)
    if not path.exists():
        return False
    path.unlink()
    # Also remove parquet/csv if exists
    for ext in (".parquet", ".csv"):
        p = DATASETS_DIR / f"{dataset_id}{ext}"
        if p.exists():
            p.unlink()
    return True


def save_insight(dataset_id: str, insight: str, model: str) -> None:
    """Add AI insight to an existing dataset record."""
    path = _meta_path(dataset_id)
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["insight"] = insight
    data["insight_model"] = model
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
