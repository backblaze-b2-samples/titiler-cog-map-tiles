"""Pydantic models for the COG map Layer domain.

A Layer is the sample's primary entity: one Cloud-Optimized GeoTIFF in B2 plus a
small render-config/display sidecar. These models are the API boundary contract
(mirrored in packages/shared/src/types.ts).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Finite, selector-only option sets (the UI renders these as Select/RadioGroup,
# never free text). rio-tiler / TiTiler colormap names.
COLORMAPS = ("viridis", "terrain", "greys", "rdylgn", "magma", "plasma", "spectral")
BAND_PRESETS = ("single", "rgb")
RESAMPLINGS = ("nearest", "bilinear", "cubic")

BandPreset = Literal["single", "rgb"]
Resampling = Literal["nearest", "bilinear", "cubic"]
SampleKind = Literal["elevation", "rgb"]


class RenderConfig(BaseModel):
    """How a layer is painted into tiles. Persisted in the sidecar; re-tunable
    live in the map viewer by changing the tile URL query params."""

    band_preset: BandPreset = "single"
    colormap: str = "terrain"
    rescale_min: float | None = None
    rescale_max: float | None = None
    resampling: Resampling = "nearest"
    bidx: int = 1


class LayerSummary(BaseModel):
    id: str
    name: str
    size_bytes: int
    size_human: str
    band_count: int
    dtype: str
    minzoom: int
    maxzoom: int
    bounds: list[float]  # [w, s, e, n] WGS84
    uploaded_at: datetime


class LayerDetail(LayerSummary):
    center: list[float]  # [lng, lat, zoom]
    width: int
    height: int
    overview_levels: int
    colorinterp: list[str]
    render: RenderConfig
    # App-relative tile template the frontend prepends API_BASE to and hands to
    # Leaflet (render params are appended client-side for live re-tuning).
    tiles: str
    colormaps: list[str] = Field(default_factory=lambda: list(COLORMAPS))
    band_presets: list[str] = Field(default_factory=lambda: list(BAND_PRESETS))
    resamplings: list[str] = Field(default_factory=lambda: list(RESAMPLINGS))


class LayerStats(BaseModel):
    layer_count: int
    total_bytes: int
    total_bytes_human: str
    total_megapixels: float
    tiles_served: int


class GenerateLayerRequest(BaseModel):
    name: str
    kind: SampleKind = "elevation"
    # Optional initial render overrides. Left unset -> the server picks a sensible
    # default from the raster (RGB for 3-band, terrain colormap for single-band).
    colormap: str | None = None
    band_preset: BandPreset | None = None


class UpdateLayerRequest(BaseModel):
    name: str
    render: RenderConfig
