"""Routes for the COG map Layer management contract.

Thin HTTP layer only — all logic is in service/layers.py. These are the app's
OWN endpoints (in docs/api/openapi.json); the image tiles come from the mounted
TiTiler sub-app, which is deliberately outside this contract.

The B2-backed read handlers are sync `def` so Starlette runs blocking boto3/GDAL
work in its threadpool (same rationale as runtime/files.py). The upload handler
is async to stream the multipart body, then offloads the CPU-heavy COG
translation to the threadpool.
"""

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.service.layers import (
    LayerError,
    LayerNotFound,
    create_layer_from_upload,
    generate_sample_layer,
    get_layer,
    get_stats,
    list_layers,
    remove_layer,
    update_layer,
)
from app.types import (
    GenerateLayerRequest,
    LayerDetail,
    LayerStats,
    LayerSummary,
    UpdateLayerRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: like /files, these routes are UNAUTHENTICATED and operate on the
# single shared sample prefix (single-tenant demo — see docs/SECURITY.md). Add
# auth + per-tenant prefixes before exposing to multiple users.


def _detail_or_http(fn, *args) -> LayerDetail:
    try:
        return fn(*args)
    except LayerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except LayerNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.get("/layers", response_model=list[LayerSummary])
def list_layers_endpoint():
    return list_layers()


@router.get("/layers/stats", response_model=LayerStats)
def layer_stats_endpoint():
    return get_stats()


@router.post("/layers", response_model=LayerDetail, status_code=201)
async def create_layer_endpoint(
    file: UploadFile = File(...),
    name: str = Form(...),
    resampling: str = Form("nearest"),
    colormap: str | None = Form(None),
    band_preset: str | None = Form(None),
):
    """Ingest a GeoTIFF: convert to a COG (rio-cogeo, internal overviews) and
    store it in B2 under the sample prefix. ``colormap``/``band_preset`` are
    optional initial render overrides (unset = auto from the raster)."""
    data = await file.read()
    if len(data) > settings.max_file_size:
        raise HTTPException(status_code=413, detail="GeoTIFF too large")
    try:
        return await run_in_threadpool(
            create_layer_from_upload,
            name,
            data,
            resampling,
            colormap or None,
            band_preset or None,
        )
    except LayerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.post("/layers/generate", response_model=LayerDetail, status_code=201)
def generate_layer_endpoint(req: GenerateLayerRequest):
    """Generate a synthetic sample COG server-side (keyless) and store it in
    B2, so the demo works with zero user-supplied data."""
    return _detail_or_http(
        generate_sample_layer, req.name, req.kind, req.colormap, req.band_preset
    )


@router.get("/layers/{layer_id}", response_model=LayerDetail)
def get_layer_endpoint(layer_id: str):
    return _detail_or_http(get_layer, layer_id)


@router.patch("/layers/{layer_id}", response_model=LayerDetail)
def update_layer_endpoint(layer_id: str, req: UpdateLayerRequest):
    return _detail_or_http(update_layer, layer_id, req.name, req.render)


@router.delete("/layers/{layer_id}")
def delete_layer_endpoint(layer_id: str):
    try:
        remove_layer(layer_id)
    except LayerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except LayerNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    logger.info("Layer deleted: id=%s", layer_id)
    return {"deleted": True, "id": layer_id}
