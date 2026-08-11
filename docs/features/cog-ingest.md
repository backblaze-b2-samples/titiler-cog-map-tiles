<!-- last_verified: 2026-08-11 -->
# Feature: COG Ingest

## Purpose
Turn a raster into a **Layer** the app can serve: either upload a georeferenced
GeoTIFF (converted server-side to a valid Cloud-Optimized GeoTIFF with internal
overviews) or generate a synthetic sample COG — then store it in Backblaze B2
under the sample prefix. Keyless, CPU-only, no external provider.

## Used By
- UI: `/layers/new` (create form — "Upload GeoTIFF" or "Generate sample layer")
- API: `POST /layers` (multipart), `POST /layers/generate` (JSON)

## Core Functions
- `services/api/app/repo/cog_build.py` — `geotiff_to_cog()`: rio-cogeo `cog_translate` through in-memory GDAL files (no temp file), rejecting rasters with no CRS
- `services/api/app/repo/cog_seed.py` — `build_sample_cog()`: numpy + rasterio build a georeferenced raster over a real bbox (San Francisco), then translate to a COG with overviews
- `services/api/app/repo/cog_reader.py` — `read_cog_info_bytes()`: authoritative bounds/bands/dtype/zoom read from the in-memory COG before upload
- `services/api/app/repo/layer_store.py` — `put_cog()`, `put_sidecar()`: store the COG + render-config sidecar in B2
- `services/api/app/service/layers.py` — `create_layer_from_upload()`, `generate_sample_layer()`
- `apps/web/src/components/layers/create-layer-form.tsx` — the create form

## Canonical Files
- COG translation: `services/api/app/repo/cog_build.py`
- Seed generator: `services/api/app/repo/cog_seed.py`

## Inputs
- Upload: multipart `file` (GeoTIFF), `name`, `resampling` (nearest/bilinear/cubic), optional `colormap` / `band_preset`
- Generate: `{ name, kind: "elevation" | "rgb", colormap?, band_preset? }`

## Outputs
- A `LayerDetail` (id, name, bounds, zoom range, bands, dtype, render config, tile template)
- Side effects: `<prefix>layers/<id>.tif` (COG) and `<prefix>layers/<id>.json` (sidecar) written to B2; the shared bucket-listing cache invalidated

## Flow
- User picks a source, names the layer, submits
- Upload path: API reads the multipart body, `geotiff_to_cog` re-tiles + adds overviews, info is read from the resulting COG, the COG + sidecar are `put_object`ed to B2
- Generate path: `build_sample_cog(kind)` produces a georeferenced COG server-side, then the same store path runs
- The API returns the new `LayerDetail`; the UI navigates to `/layers/[id]`

## Edge Cases
- GeoTIFF with no CRS → 422 with a clear message (`geotiff_to_cog` raises `CogError`)
- Upload larger than `max_file_size` → 413
- Empty name → 400

## UX States
- Empty: source selector defaults to "Generate sample layer" (works with no data)
- Loading: submit button shows "Working…" while the COG is translated/uploaded
- Error: toast with the server detail; the form stays filled

## Verification
- Test files: `services/api/tests/test_cog_pipeline.py`, `services/api/tests/test_layers.py`
- Required cases: seed COG is valid + georeferenced + has overviews and renders a real PNG tile; `geotiff_to_cog` rejects a non-georeferenced raster; create/generate routes map errors to 422/400/413
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Tile Serving](tile-serving.md)
- [COG Info](cog-info.md)
- [App Workflows](../app-workflows.md)
