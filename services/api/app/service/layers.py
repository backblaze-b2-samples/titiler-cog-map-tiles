"""Domain logic for COG map Layers.

Orchestrates the repo adapters (boto3 storage, rio-tiler reads, rio-cogeo
translation, the synthetic seed generator, the tiles-served counter) into the
Layer lifecycle the API exposes. No boto3/GDAL here — that all lives in repo/.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.repo import (
    CogError,
    build_sample_cog,
    cog_exists,
    delete_layer,
    geotiff_to_cog,
    get_sidecar,
    get_tiles_served,
    head_cog,
    increment_tiles_served,
    is_valid_layer_id,
    layer_s3_url,
    list_layer_ids,
    put_cog,
    put_sidecar,
    read_band_range,
    read_cog_info,
    read_cog_info_bytes,
    total_cog_bytes,
)
from app.repo.cog_reader import CogInfo
from app.types import LayerDetail, LayerStats, LayerSummary, RenderConfig
from app.types.formatting import humanize_bytes

# Tile template the frontend prepends API_BASE to and hands to Leaflet. Render
# query params (colormap, rescale, resampling…) are appended client-side so the
# map viewer can re-tune a layer live without a server round-trip.
_TMS = "WebMercatorQuad"


class LayerError(Exception):
    """Invalid Layer input (bad name, un-georeferenced upload, bad id)."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class LayerNotFound(Exception):
    def __init__(self, detail: str = "Layer not found"):
        self.detail = detail
        super().__init__(detail)


def _tiles_template(layer_id: str) -> str:
    return f"/tiler/tiles/{_TMS}/{{z}}/{{x}}/{{y}}.png?layer={layer_id}"


def _sanitize_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise LayerError("Layer name is required")
    return name[:120]


def _default_render(info: CogInfo, band_range: tuple[float, float] | None) -> RenderConfig:
    """A sensible default render config for a freshly ingested COG."""
    if info.band_count >= 3:
        return RenderConfig(band_preset="rgb", colormap="viridis", resampling="nearest")
    lo, hi = (band_range if band_range else (None, None))
    return RenderConfig(
        band_preset="single",
        colormap="terrain",
        rescale_min=lo,
        rescale_max=hi,
        resampling="nearest",
    )


def _sidecar(name: str, info: CogInfo, render: RenderConfig) -> dict:
    return {
        "name": name,
        "bounds": list(info.bounds),
        "center": list(info.center),
        "minzoom": info.minzoom,
        "maxzoom": info.maxzoom,
        "band_count": info.band_count,
        "dtype": info.dtype,
        "width": info.width,
        "height": info.height,
        "overview_levels": info.overview_levels,
        "colorinterp": info.colorinterp,
        "render": render.model_dump(),
        "created_at": datetime.now(UTC).isoformat(),
    }


def _summary(layer_id: str, sidecar: dict, head: dict) -> LayerSummary:
    size = head["size_bytes"]
    return LayerSummary(
        id=layer_id,
        name=sidecar.get("name", layer_id),
        size_bytes=size,
        size_human=humanize_bytes(size),
        band_count=sidecar.get("band_count", 0),
        dtype=sidecar.get("dtype", ""),
        minzoom=sidecar.get("minzoom", 0),
        maxzoom=sidecar.get("maxzoom", 0),
        bounds=sidecar.get("bounds", [0, 0, 0, 0]),
        uploaded_at=head["last_modified"],
    )


def _detail(layer_id: str, sidecar: dict, head: dict) -> LayerDetail:
    base = _summary(layer_id, sidecar, head)
    return LayerDetail(
        **base.model_dump(),
        center=sidecar.get("center", [0, 0, 0]),
        width=sidecar.get("width", 0),
        height=sidecar.get("height", 0),
        overview_levels=sidecar.get("overview_levels", 0),
        colorinterp=sidecar.get("colorinterp", []),
        render=RenderConfig(**sidecar.get("render", {})),
        tiles=_tiles_template(layer_id),
    )


def _ensure_sidecar(layer_id: str) -> dict:
    """Read a layer's sidecar, rebuilding it from the COG if it's missing.

    Layers created through the app always have a sidecar; this fallback keeps
    the app honest if a bare COG was dropped under the prefix out-of-band.
    """
    sidecar = get_sidecar(layer_id)
    if sidecar is not None:
        return sidecar
    src = layer_s3_url(layer_id)
    info = read_cog_info(src)  # network read; only on the rare no-sidecar path
    render = _default_render(info, read_band_range(src, 1))
    sidecar = _sidecar(layer_id, info, render)
    put_sidecar(layer_id, sidecar)
    return sidecar


def list_layers() -> list[LayerSummary]:
    summaries: list[LayerSummary] = []
    for layer_id in list_layer_ids():
        head = head_cog(layer_id)
        if head is None:
            continue
        try:
            sidecar = _ensure_sidecar(layer_id)
        except (CogError, RuntimeError):
            sidecar = {"name": layer_id}
        summaries.append(_summary(layer_id, sidecar, head))
    summaries.sort(key=lambda layer: layer.uploaded_at, reverse=True)
    return summaries


def get_layer(layer_id: str) -> LayerDetail:
    if not is_valid_layer_id(layer_id):
        raise LayerError("Invalid layer id")
    head = head_cog(layer_id)
    if head is None:
        raise LayerNotFound()
    return _detail(layer_id, _ensure_sidecar(layer_id), head)


def _apply_override(
    render: RenderConfig, colormap: str | None, band_preset: str | None
) -> RenderConfig:
    """Override the computed default render with any explicit user choices."""
    update: dict = {}
    if band_preset:
        update["band_preset"] = band_preset
    if colormap:
        update["colormap"] = colormap
    return render.model_copy(update=update) if update else render


def _persist_new(
    name: str,
    cog_bytes: bytes,
    colormap: str | None = None,
    band_preset: str | None = None,
) -> LayerDetail:
    """Read info from the in-memory COG, then store the COG + sidecar in B2."""
    layer_id = uuid.uuid4().hex
    info, band_range = read_cog_info_bytes(cog_bytes)
    render = _apply_override(_default_render(info, band_range), colormap, band_preset)
    put_cog(layer_id, cog_bytes)
    put_sidecar(layer_id, _sidecar(name, info, render))
    head = head_cog(layer_id) or {
        "size_bytes": len(cog_bytes),
        "last_modified": datetime.now(UTC),
    }
    return _detail(layer_id, _ensure_sidecar(layer_id), head)


def create_layer_from_upload(
    name: str,
    data: bytes,
    resampling: str,
    colormap: str | None = None,
    band_preset: str | None = None,
) -> LayerDetail:
    name = _sanitize_name(name)
    if not data:
        raise LayerError("Empty upload")
    try:
        cog_bytes = geotiff_to_cog(data, resampling=resampling)
    except CogError as exc:
        raise LayerError(str(exc), status_code=422) from None
    return _persist_new(name, cog_bytes, colormap, band_preset)


def generate_sample_layer(
    name: str,
    kind: str,
    colormap: str | None = None,
    band_preset: str | None = None,
) -> LayerDetail:
    name = _sanitize_name(name)
    cog_bytes = build_sample_cog(kind)
    return _persist_new(name, cog_bytes, colormap, band_preset)


def update_layer(layer_id: str, name: str, render: RenderConfig) -> LayerDetail:
    if not is_valid_layer_id(layer_id):
        raise LayerError("Invalid layer id")
    head = head_cog(layer_id)
    if head is None:
        raise LayerNotFound()
    sidecar = _ensure_sidecar(layer_id)
    sidecar["name"] = _sanitize_name(name)
    sidecar["render"] = render.model_dump()
    put_sidecar(layer_id, sidecar)
    return _detail(layer_id, sidecar, head)


def remove_layer(layer_id: str) -> None:
    if not is_valid_layer_id(layer_id):
        raise LayerError("Invalid layer id")
    if not cog_exists(layer_id):
        raise LayerNotFound()
    delete_layer(layer_id)


def get_stats() -> LayerStats:
    ids = list_layer_ids()
    megapixels = 0.0
    for layer_id in ids:
        sidecar = get_sidecar(layer_id)
        if sidecar:
            megapixels += sidecar.get("width", 0) * sidecar.get("height", 0) / 1_000_000
    total = total_cog_bytes()
    return LayerStats(
        layer_count=len(ids),
        total_bytes=total,
        total_bytes_human=humanize_bytes(total),
        total_megapixels=round(megapixels, 1),
        tiles_served=get_tiles_served(),
    )


def record_tile_served() -> None:
    increment_tiles_served()
