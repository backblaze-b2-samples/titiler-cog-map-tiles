"""GDAL / VSI-S3 configuration for reading COG byte-ranges from Backblaze B2.

GDAL (used by rasterio / rio-tiler / TiTiler) reads Cloud-Optimized GeoTIFFs
directly from B2 over the S3-compatible API via its ``/vsis3/`` virtual
filesystem — the S3 Range-GET pattern that makes COG-from-object-storage work
with zero data duplication.

GDAL has no boto3 client, so its custom User-Agent (Standard #2) is set through
the ``GDAL_HTTP_USERAGENT`` env var — the only mechanism GDAL offers, analogous
to the DuckDB ``http_agent`` / PyArrow cases. The value is the SAME attribution
token as the boto3 ``user_agent_extra`` on the B2 S3 client, so B2's two S3
access paths report one identity. Every value derives from the ``B2_*`` settings;
no endpoint host or region is hardcoded here.

boto3/GDAL config stays in ``repo/`` (AGENTS.md §3).
"""

import os
import re

from app.config import settings

# One attribution token — identical to user_agent_extra in repo/b2_client.py.
B2_USER_AGENT = "b2ai-titiler-cog"

# Layer ids are app-minted (uuid4 hex or a slug); this is the SSRF gate that
# stops the mounted tiler from opening any path outside the sample prefix.
_LAYER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def is_valid_layer_id(layer_id: str) -> bool:
    """True for a safe layer id (alphanumeric / dash / underscore, no slashes)."""
    return bool(_LAYER_ID_RE.match(layer_id))


def layers_prefix() -> str:
    """Prefix every Layer object lives under, inside the sample's own prefix."""
    return f"{settings.sample_prefix}layers/"


def cog_key(layer_id: str) -> str:
    """B2 object key for a layer's COG (``<prefix>layers/<id>.tif``)."""
    return f"{layers_prefix()}{layer_id}.tif"


def sidecar_key(layer_id: str) -> str:
    """B2 object key for a layer's render-config sidecar JSON."""
    return f"{layers_prefix()}{layer_id}.json"


def layer_s3_url(layer_id: str) -> str:
    """``s3://`` URL GDAL reads a layer's COG byte-ranges from.

    Only ever built from a validated id and always inside the sample prefix, so
    the tiler never opens an arbitrary path.
    """
    return f"s3://{settings.b2_bucket_name}/{cog_key(layer_id)}"


def configure_gdal_s3() -> None:
    """Apply the GDAL/VSI-S3 environment from ``B2_*`` settings.

    Called once at startup (main.py) BEFORE rasterio is first used — rasterio
    reads the GDAL env when it first opens a dataset. No-op without credentials
    (test collection has none), so the env is never left half-configured.
    """
    if not (settings.b2_application_key_id and settings.b2_application_key):
        return
    env = {
        # Host only, no scheme — this is what GDAL's AWS_S3_ENDPOINT expects.
        "AWS_S3_ENDPOINT": settings.s3_endpoint_host,
        "AWS_ACCESS_KEY_ID": settings.b2_application_key_id,
        "AWS_SECRET_ACCESS_KEY": settings.b2_application_key,
        "AWS_REGION": settings.b2_region,
        # B2 needs path-style addressing (bucket in the path, not the host).
        "AWS_VIRTUAL_HOSTING": "FALSE",
        "AWS_HTTPS": "YES",
        # Critical: stop GDAL probing the "directory" on every open.
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff",
        "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
        "GDAL_HTTP_MULTIPLEX": "YES",
        "VSI_CACHE": "TRUE",
        "VSI_CACHE_SIZE": "536870912",  # 512 MiB per-process range cache
        "GDAL_HTTP_USERAGENT": B2_USER_AGENT,
    }
    # Explicit set (not setdefault): the app is the authority for how the tiler
    # talks to B2, so ambient AWS_* shell vars must not shadow the B2 config.
    os.environ.update(env)
