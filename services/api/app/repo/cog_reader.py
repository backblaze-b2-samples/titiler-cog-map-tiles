"""Read COG geospatial metadata with rio-tiler.

rio-tiler's ``Reader`` opens a dataset through rasterio/GDAL. For a B2-hosted
COG the src path is an ``s3://`` URL (see ``gdal_s3.layer_s3_url``) and GDAL
fetches only the byte-ranges rio-tiler asks for; for a freshly translated COG
still in memory it is a ``/vsimem/`` path. This module reads *metadata only* — no
tile rendering (that is TiTiler's mounted sub-app).

rio-tiler/GDAL stays in ``repo/`` (AGENTS.md §3).
"""

from __future__ import annotations

from dataclasses import dataclass

from rasterio.io import MemoryFile
from rio_tiler.constants import WGS84_CRS
from rio_tiler.io import Reader


class CogError(Exception):
    """Raised when a source is not a readable, georeferenced raster / COG."""


@dataclass(frozen=True)
class CogInfo:
    bounds: tuple[float, float, float, float]  # w, s, e, n (WGS84)
    center: tuple[float, float, int]  # lng, lat, minzoom
    minzoom: int
    maxzoom: int
    band_count: int
    dtype: str
    width: int
    height: int
    overview_levels: int
    colorinterp: list[str]


def read_cog_info(src_path: str) -> CogInfo:
    """Open ``src_path`` with rio-tiler and return its geospatial metadata.

    Raises ``CogError`` if the source cannot be opened or has no CRS.
    """
    try:
        with Reader(src_path) as cog:
            ds = cog.dataset
            if ds.crs is None:
                raise CogError("raster has no CRS (not georeferenced)")
            w, s, e, n = cog.get_geographic_bounds(WGS84_CRS)
            minzoom = int(cog.minzoom)
            maxzoom = int(cog.maxzoom)
            return CogInfo(
                bounds=(float(w), float(s), float(e), float(n)),
                center=((float(w) + float(e)) / 2, (float(s) + float(n)) / 2, minzoom),
                minzoom=minzoom,
                maxzoom=maxzoom,
                band_count=int(ds.count),
                dtype=str(ds.dtypes[0]),
                width=int(ds.width),
                height=int(ds.height),
                overview_levels=len(ds.overviews(1)),
                colorinterp=[ci.name for ci in ds.colorinterp],
            )
    except CogError:
        raise
    except Exception as exc:  # rasterio/rio-tiler raise a wide range of errors
        raise CogError(f"could not read COG at {src_path}: {exc}") from exc


def read_cog_info_bytes(data: bytes) -> tuple[CogInfo, tuple[float, float] | None]:
    """Read geospatial info + a suggested band-1 rescale from in-memory COG bytes.

    Used right after translation/generation so metadata is authoritative without
    a B2 round-trip. rasterio's ``MemoryFile`` registers the bytes at a
    ``/vsimem/`` path that rio-tiler opens while the context is active.
    """
    with MemoryFile(data) as mem:
        info = read_cog_info(mem.name)
        band_range = read_band_range(mem.name, 1)
    return info, band_range


def read_band_range(src_path: str, band: int = 1) -> tuple[float, float] | None:
    """Suggest a rescale (min, max) for ``band`` from decimated statistics.

    rio-tiler reads an overview, not the full raster, so this stays cheap. Uses
    the 2nd/98th percentiles for nicer default contrast, falling back to
    min/max. Returns ``None`` if statistics can't be computed.
    """
    try:
        with Reader(src_path) as cog:
            stats = cog.statistics()
        key = f"b{band}" if f"b{band}" in stats else next(iter(stats))
        band_stats = stats[key]
        lo = getattr(band_stats, "percentile_2", None)
        hi = getattr(band_stats, "percentile_98", None)
        if lo is None or hi is None:
            lo, hi = band_stats.min, band_stats.max
        lo, hi = float(lo), float(hi)
        if lo == hi:
            return None
        return (lo, hi)
    except Exception:
        return None
