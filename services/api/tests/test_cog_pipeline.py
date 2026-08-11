"""End-to-end COG pipeline tests — the marquee tile-render path, no network.

Everything here runs on in-memory GDAL files (``/vsimem/``), so it is hermetic
(the conftest network guard is respected) yet exercises the REAL raster stack:
synthetic seed generation -> rio-cogeo translation -> rio-tiler info -> an actual
rendered PNG tile. Import-only green would not catch a broken native set; these
would.
"""

import morecantile
import numpy as np
import pytest
from rasterio.io import MemoryFile
from rio_tiler.io import Reader

from app.repo.cog_build import geotiff_to_cog
from app.repo.cog_reader import CogError, read_cog_info, read_cog_info_bytes
from app.repo.cog_seed import SAMPLE_KINDS, build_sample_cog

_TMS = morecantile.tms.get("WebMercatorQuad")


def _is_tiff(data: bytes) -> bool:
    return data[:4] in (b"II*\x00", b"MM\x00*")


@pytest.mark.parametrize("kind", SAMPLE_KINDS)
def test_build_sample_cog_is_valid_georeferenced_with_overviews(kind):
    cog = build_sample_cog(kind)
    assert _is_tiff(cog)
    info, band_range = read_cog_info_bytes(cog)
    assert info.band_count == (3 if kind == "rgb" else 1)
    # Overlays San Francisco: geographic bounds sit within the seed bbox.
    w, s, e, n = info.bounds
    assert -123 < w < e < -122
    assert 37 < s < n < 38
    assert info.minzoom <= info.maxzoom
    # Internal overviews are required for multi-zoom tiles.
    assert info.overview_levels >= 1
    if kind == "elevation":
        assert band_range is not None and band_range[0] < band_range[1]


def test_seed_cog_renders_a_real_png_tile():
    cog = build_sample_cog("rgb")
    with MemoryFile(cog) as mem:
        info = read_cog_info(mem.name)
        with Reader(mem.name) as reader:
            lng, lat, _ = info.center
            tile = _TMS.tile(lng, lat, info.minzoom + 1)
            png = reader.tile(tile.x, tile.y, tile.z).render(img_format="PNG")
    assert png[:4] == b"\x89PNG"
    assert len(png) > 100


def test_geotiff_to_cog_rejects_non_georeferenced_raster():
    array = np.zeros((1, 16, 16), dtype="uint8")
    with MemoryFile() as mem:
        with mem.open(driver="GTiff", count=1, height=16, width=16, dtype="uint8") as dst:
            dst.write(array)
        mem.seek(0)
        plain_tiff = mem.read()
    with pytest.raises(CogError):
        geotiff_to_cog(plain_tiff)
