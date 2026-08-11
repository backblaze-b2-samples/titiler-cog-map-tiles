"""Convert an uploaded GeoTIFF into a valid COG (with internal overviews).

rio-cogeo's ``cog_translate`` does the raster work — it re-tiles, adds internal
overviews (needed for multi-zoom tiles), and writes a COG. Everything runs
through in-memory GDAL files (``MemoryFile`` / ``/vsimem/``) so bytes go straight
to and from B2 without a temp file on disk.

rasterio/rio-cogeo stays in ``repo/`` (AGENTS.md §3).
"""

from __future__ import annotations

from rasterio.io import MemoryFile
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles

from app.repo.cog_reader import CogError

# rio-cogeo resampling names for building overviews.
RESAMPLINGS = ("nearest", "bilinear", "cubic")


def geotiff_to_cog(data: bytes, *, resampling: str = "nearest") -> bytes:
    """Return valid COG bytes (deflate-compressed, internal overviews) for a
    georeferenced GeoTIFF given as ``data``.

    Raises ``CogError`` if the input is not a readable, georeferenced raster.
    """
    if resampling not in RESAMPLINGS:
        resampling = "nearest"
    try:
        with MemoryFile(data) as src_mem, src_mem.open() as src:
            if src.crs is None:
                raise CogError("GeoTIFF has no CRS — upload a georeferenced raster")
            dst_profile = cog_profiles.get("deflate")
            with MemoryFile() as dst_mem:
                cog_translate(
                    src,
                    dst_mem.name,
                    dst_profile,
                    in_memory=True,
                    overview_resampling=resampling,
                    quiet=True,
                )
                dst_mem.seek(0)
                return dst_mem.read()
    except CogError:
        raise
    except Exception as exc:
        raise CogError(f"COG translation failed: {exc}") from exc
