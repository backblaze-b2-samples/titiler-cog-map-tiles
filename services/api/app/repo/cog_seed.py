"""Synthetic, keyless, reproducible seed COGs (numpy + rasterio + rio-cogeo).

Builds properly georeferenced rasters over a REAL-world bbox (San Francisco) so
they overlay OpenStreetMap at a recognizable place, then translates them to valid
COGs with internal overviews. No external download, no API key — the demo works
with zero user-supplied data and ~$0/run.

Two kinds:
  - ``rgb``:       3-band uint8 false-color pattern (renders natively as RGB).
  - ``elevation``: 1-band float32 smooth terrain-like surface (colormap + rescale).

rasterio/numpy stays in ``repo/`` (AGENTS.md §3).
"""

from __future__ import annotations

import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds

from app.repo.cog_build import geotiff_to_cog

# San Francisco peninsula (w, s, e, n) in WGS84 — a recognizable OSM location.
SF_BBOX = (-122.52, 37.70, -122.36, 37.83)
_SIZE = 1024  # px per side — enough resolution for several overview levels

SAMPLE_KINDS = ("elevation", "rgb")


def _grids() -> tuple[np.ndarray, np.ndarray]:
    """Normalized [0,1] coordinate grids for the raster (row-major)."""
    ys = np.linspace(0.0, 1.0, _SIZE, dtype=np.float32)
    xs = np.linspace(0.0, 1.0, _SIZE, dtype=np.float32)
    return np.meshgrid(xs, ys)  # gx, gy


def _elevation_surface() -> np.ndarray:
    """A smooth, terrain-like float32 surface (a couple of hills + a ridge)."""
    gx, gy = _grids()
    hill_a = np.exp(-(((gx - 0.32) ** 2 + (gy - 0.55) ** 2) / 0.03))
    hill_b = np.exp(-(((gx - 0.70) ** 2 + (gy - 0.35) ** 2) / 0.05))
    ridge = 0.35 * (np.sin(gx * 7.0) * np.cos(gy * 5.0))
    surface = 40.0 + 900.0 * hill_a + 650.0 * hill_b + 120.0 * ridge
    return surface.astype(np.float32)


def _rgb_stack() -> np.ndarray:
    """A 3-band uint8 false-color pattern derived from smooth signals."""
    gx, gy = _grids()
    r = 0.5 + 0.5 * np.sin(gx * 6.0 + gy * 2.0)
    g = 0.5 + 0.5 * np.sin(gy * 6.0 - gx * 3.0 + 1.5)
    b = 0.5 + 0.5 * np.cos((gx + gy) * 5.0)
    stack = np.stack([r, g, b]) * 255.0
    return stack.clip(0, 255).astype(np.uint8)


def _write_geotiff(array: np.ndarray) -> bytes:
    """Write a georeferenced GeoTIFF (EPSG:4326) for a (bands, h, w) array."""
    if array.ndim == 2:
        array = array[np.newaxis, :, :]
    count, height, width = array.shape
    transform = from_bounds(*SF_BBOX, width, height)
    profile = {
        "driver": "GTiff",
        "dtype": array.dtype,
        "count": count,
        "height": height,
        "width": width,
        "crs": "EPSG:4326",
        "transform": transform,
    }
    with MemoryFile() as mem:
        with mem.open(**profile) as dst:
            dst.write(array)
        mem.seek(0)
        return mem.read()


def build_sample_cog(kind: str) -> bytes:
    """Return valid COG bytes (with overviews) for a synthetic sample layer."""
    if kind == "rgb":
        geotiff = _write_geotiff(_rgb_stack())
    else:  # default to elevation
        geotiff = _write_geotiff(_elevation_surface())
    return geotiff_to_cog(geotiff, resampling="bilinear")
