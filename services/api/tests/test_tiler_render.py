"""The mounted tiler's HTTP contract: a real rendered PNG through TiTiler.

Serves a locally-generated seed COG through a real ``TilerFactory`` over ASGI
(no sockets, so the network guard is respected). This proves the "run" verb's
HTTP path end-to-end — the tile route shape, the exact render query params the
frontend builds (`apps/web/src/lib/layer-render.ts`), and that a genuine PNG
comes back — without needing B2. It is not import-only green.
"""

import morecantile
import pytest
from fastapi import FastAPI, Query
from httpx import ASGITransport, AsyncClient
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.factory import TilerFactory

from app.repo.cog_reader import read_cog_info
from app.repo.cog_seed import build_sample_cog

_TMS = morecantile.tms.get("WebMercatorQuad")


@pytest.fixture
def tiler_client(tmp_path):
    """A tiler app whose dataset path is a local seed COG file."""
    cog_path = tmp_path / "seed.tif"
    cog_path.write_bytes(build_sample_cog("elevation"))
    info = read_cog_info(str(cog_path))

    app = FastAPI()

    def path_dependency(layer: str = Query(...)) -> str:
        return str(cog_path)

    factory = TilerFactory(path_dependency=path_dependency)
    app.include_router(factory.router)
    add_exception_handlers(app, DEFAULT_STATUS_CODES)
    return app, info


async def test_renders_a_real_png_with_frontend_render_params(tiler_client):
    app, info = tiler_client
    lng, lat, _ = info.center
    tile = _TMS.tile(lng, lat, info.minzoom + 1)
    # Exactly what apps/web/src/lib/layer-render.ts builds for a single-band layer.
    url = (
        f"/tiles/WebMercatorQuad/{tile.z}/{tile.x}/{tile.y}.png"
        "?layer=abc&colormap_name=terrain&rescale=35,766&bidx=1&resampling=nearest"
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://tiler"
    ) as client:
        res = await client.get(url)
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content[:4] == b"\x89PNG"
    assert len(res.content) > 100


async def test_tile_outside_bounds_is_404_not_500(tiler_client):
    app, _ = tiler_client
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://tiler"
    ) as client:
        # z=2 world tile far from the SF COG -> outside bounds.
        res = await client.get(
            "/tiles/WebMercatorQuad/2/0/0.png?layer=abc&colormap_name=terrain"
        )
    assert res.status_code == 404
