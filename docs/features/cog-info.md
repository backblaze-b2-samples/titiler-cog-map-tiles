<!-- last_verified: 2026-08-11 -->
# Feature: COG Info

## Purpose
Read a COG's geospatial metadata — geographic bounds, band count, dtype, internal
overview levels, and the zoom range — with rio-tiler, so the library and detail
views can describe a layer and the map can center on it. Read at ingest time from
the in-memory COG (authoritative, no B2 round-trip) and cached in the sidecar.

## Used By
- UI: `/layers/[id]` "COG info" panel; badges on `/layers`
- API: `GET /layers/{layer_id}` (detail carries the cached info)

## Core Functions
- `services/api/app/repo/cog_reader.py` — `read_cog_info()` (bounds via `get_geographic_bounds(WGS84_CRS)`, `minzoom`/`maxzoom`, band count, dtype, overviews, colorinterp), `read_cog_info_bytes()`, `read_band_range()` (decimated statistics → default rescale)
- `services/api/app/service/layers.py` — caches the info into the sidecar and builds `LayerDetail`

## Canonical Files
- COG reader: `services/api/app/repo/cog_reader.py`

## Inputs
- A COG source path (`/vsimem/` for freshly translated bytes, or `s3://…` for a stored layer)

## Outputs
- `CogInfo` (bounds, center, minzoom, maxzoom, band_count, dtype, width, height, overview_levels, colorinterp)
- An optional band-1 `(min, max)` rescale suggestion

## Flow
- At ingest, `read_cog_info_bytes()` opens the in-memory COG and reads its metadata + a suggested rescale; the result is written into the sidecar
- `GET /layers/{id}` returns the cached info as `LayerDetail`

## Edge Cases
- Source with no CRS → `CogError` (surfaced as 422 on ingest)
- Statistics unavailable → rescale suggestion is `None` (auto-scale at render time)

## UX States
- Rendered as a metrics panel on the detail page; badges on library rows

## Verification
- Test files: `services/api/tests/test_cog_pipeline.py`
- Required cases: seed COGs report the SF bbox, the right band count/dtype, overviews ≥ 1, and a valid zoom range
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [COG Ingest](cog-ingest.md)
- [Tile Serving](tile-serving.md)
- [App Workflows](../app-workflows.md)
