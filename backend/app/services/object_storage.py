import os
from pathlib import Path


def _endpoint_url() -> str | None:
    explicit = os.getenv("R2_ENDPOINT_URL")
    if explicit:
        return explicit
    account_id = os.getenv("R2_ACCOUNT_ID")
    if account_id:
        return f"https://{account_id}.r2.cloudflarestorage.com"
    return None


def _enabled() -> bool:
    required = (
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
    )
    return bool(_endpoint_url()) and all(os.getenv(k) for k in required)


def _client():
    if not _enabled():
        return None
    try:
        import boto3
    except Exception:
        return None
    return boto3.client(
        "s3",
        endpoint_url=_endpoint_url(),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name=os.getenv("R2_REGION", "auto"),
    )


def object_key(dataset_id: str, path: Path) -> str:
    prefix = os.getenv("R2_PREFIX", "datasets").strip("/")
    return f"{prefix}/{dataset_id}/{path.name}"


def upload_dataset_artifact(dataset_id: str, path: Path) -> str | None:
    client = _client()
    if client is None or not path.exists():
        return None
    key = object_key(dataset_id, path)
    try:
        client.upload_file(str(path), os.getenv("R2_BUCKET"), key)
        return key
    except Exception:
        return None


def download_dataset_artifact(dataset_id: str, filename: str, destination: Path) -> bool:
    client = _client()
    if client is None:
        return False
    key = object_key(dataset_id, Path(filename))
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(os.getenv("R2_BUCKET"), key, str(destination))
        return destination.exists()
    except Exception:
        return False


def delete_dataset_artifacts(dataset_id: str) -> None:
    client = _client()
    if client is None:
        return
    bucket = os.getenv("R2_BUCKET")
    prefix = f"{os.getenv('R2_PREFIX', 'datasets').strip('/')}/{dataset_id}/"
    try:
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if objects:
                client.delete_objects(Bucket=bucket, Delete={"Objects": objects})
    except Exception:
        return
