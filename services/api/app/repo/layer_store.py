"""Persistence for COG map Layers in B2 (S3 API), scoped to the sample prefix.

A Layer = one COG object (``<id>.tif``) + one small sidecar JSON (``<id>.json``)
holding its display name, cached geospatial metadata, and default render config.
Both live under ``<sample_prefix>layers/``. boto3 stays in ``repo/`` (AGENTS.md
§3) and the shared cached S3 client is reused from ``b2_client`` for connection
pooling. Every write invalidates the shared full-bucket listing cache so the
new/removed object shows up in the ``/files`` explorer and stats immediately.
"""

from __future__ import annotations

import io
import json

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.gdal_s3 import cog_key, layers_prefix, sidecar_key
from app.repo.list_cache import invalidate as _invalidate_list_cache


def list_layer_ids() -> list[str]:
    """Every layer id under the sample prefix (from the ``.tif`` objects)."""
    client = get_s3_client()
    prefix = layers_prefix()
    ids: list[str] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".tif"):
                    ids.append(key[len(prefix) : -len(".tif")])
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed: {e}") from e
    return ids


def head_cog(layer_id: str) -> dict | None:
    """``{size_bytes, last_modified}`` for a layer's COG, or ``None`` if absent."""
    client = get_s3_client()
    try:
        resp = client.head_object(Bucket=settings.b2_bucket_name, Key=cog_key(layer_id))
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 head failed for layer '{layer_id}': {e}") from e
    return {"size_bytes": resp["ContentLength"], "last_modified": resp["LastModified"]}


def cog_exists(layer_id: str) -> bool:
    return head_cog(layer_id) is not None


def put_cog(layer_id: str, data: bytes) -> None:
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=cog_key(layer_id),
            Body=io.BytesIO(data),
            ContentType="image/tiff",
        )
    except ClientError as e:
        raise RuntimeError(f"B2 upload failed for layer '{layer_id}': {e}") from e
    _invalidate_list_cache()


def put_sidecar(layer_id: str, sidecar: dict) -> None:
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=sidecar_key(layer_id),
            Body=json.dumps(sidecar, separators=(",", ":")).encode("utf-8"),
            ContentType="application/json",
        )
    except ClientError as e:
        raise RuntimeError(f"B2 sidecar write failed for layer '{layer_id}': {e}") from e
    _invalidate_list_cache()


def get_sidecar(layer_id: str) -> dict | None:
    client = get_s3_client()
    try:
        resp = client.get_object(Bucket=settings.b2_bucket_name, Key=sidecar_key(layer_id))
        return json.loads(resp["Body"].read())
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 sidecar read failed for layer '{layer_id}': {e}") from e
    except (json.JSONDecodeError, ValueError):
        return None


def delete_layer(layer_id: str) -> None:
    """Delete a layer's COG and sidecar. Scoped to the sample prefix by key."""
    client = get_s3_client()
    for key in (cog_key(layer_id), sidecar_key(layer_id)):
        try:
            client.delete_object(Bucket=settings.b2_bucket_name, Key=key)
        except ClientError as e:
            raise RuntimeError(f"B2 delete failed for '{key}': {e}") from e
    _invalidate_list_cache()


def total_cog_bytes() -> int:
    """Sum of every layer COG's size — for the geospatial dashboard."""
    client = get_s3_client()
    prefix = layers_prefix()
    total = 0
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            total += sum(o["Size"] for o in resp.get("Contents", []) if o["Key"].endswith(".tif"))
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed: {e}") from e
    return total
