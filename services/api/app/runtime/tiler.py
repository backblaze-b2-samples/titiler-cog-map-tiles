"""The mounted TiTiler tile sub-app + the tiles-served counter middleware.

TiTiler is mounted (in main.py) as a SUB-APP at ``/tiler`` rather than merged via
``include_router``: a mounted app has its OWN OpenAPI, so TiTiler's ~15 raster
routes stay OUT of ``docs/api/openapi.json`` and the API contract test. The
browser only reads image tiles from it (Leaflet ``L.tileLayer`` = ``<img>``
requests), which are not CORS-gated, so the sub-app needs no CORS middleware.

SSRF safety: the tiler never accepts a raw ``?url=``. Its ``path_dependency``
takes a ``layer`` id, validates its shape, and maps it to
``s3://<bucket>/<sample-prefix>/layers/<id>.tif`` — always inside the sample
prefix, never an arbitrary path.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request, Response
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.factory import TilerFactory

from app.repo import is_valid_layer_id, layer_s3_url

# Full path (from the parent app's perspective) of a rendered XYZ tile. The
# frontend builds tile URLs against this; the middleware below matches it to
# count served tiles.
TILE_PATH_PREFIX = "/tiler/tiles/"


def layer_path_dependency(
    layer: str = Query(..., description="Layer id within the sample prefix"),
) -> str:
    """Resolve the ``layer`` query param to a constrained s3:// COG path."""
    if not is_valid_layer_id(layer):
        raise HTTPException(status_code=400, detail="Invalid layer id")
    return layer_s3_url(layer)


def build_tiler_app() -> FastAPI:
    """A minimal FastAPI sub-app exposing TiTiler's COG endpoints, constrained
    to the sample's layers. Docs/OpenAPI disabled so it stays out of the
    contract surface."""
    tiler = FastAPI(
        title="TiTiler tile sub-app",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    cog = TilerFactory(path_dependency=layer_path_dependency)
    tiler.include_router(cog.router)
    # Map rio-tiler errors to proper status codes (e.g. a tile outside the COG
    # bounds → 404, which Leaflet handles gracefully) instead of a bare 500.
    add_exception_handlers(tiler, DEFAULT_STATUS_CODES)
    return tiler


async def tiles_served_middleware(request: Request, call_next) -> Response:
    """Increment the durable tiles-served counter on each successful tile."""
    response = await call_next(request)
    if (
        request.method == "GET"
        and response.status_code == 200
        and request.url.path.startswith(TILE_PATH_PREFIX)
    ):
        # runtime -> service -> repo; kept a local import to avoid a heavy
        # module-load cost on the hot middleware path.
        from app.service.layers import record_tile_served

        record_tile_served()
    return response
