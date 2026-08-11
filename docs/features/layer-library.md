<!-- last_verified: 2026-08-11 -->
# Feature: Layer Library

## Purpose
The sample-scoped explorer: `/layers` lists every COG layer in the sample prefix
(`titiler-cog-map-tiles/layers/`) with its name, band count, dtype, zoom range,
and size. It sits **alongside** the untouched full-bucket `/files` explorer — the
library is scoped to just this app's layers.

## Used By
- UI: `/layers` (library list), row action → delete; row link → `/layers/[id]`
- API: `GET /layers`, `DELETE /layers/{layer_id}`

## Core Functions
- `services/api/app/service/layers.py` — `list_layers()` (reads each layer's sidecar + HEAD), `remove_layer()`
- `services/api/app/repo/layer_store.py` — `list_layer_ids()`, `head_cog()`, `delete_layer()`
- `apps/web/src/components/layers/layer-library.tsx` — the table
- `apps/web/src/components/layers/delete-layer-dialog.tsx` — the AlertDialog confirm
- `apps/web/src/lib/queries.ts` — `useLayers()`, `useDeleteLayer()`

## Canonical Files
- Library table: `apps/web/src/components/layers/layer-library.tsx`
- Listing service: `services/api/app/service/layers.py`

## Inputs
- None (lists the sample prefix)

## Outputs
- `LayerSummary[]` (id, name, size, bands, dtype, zoom range, bounds, uploaded_at)

## Flow
- `list_layer_ids()` lists `.tif` objects under the sample prefix
- For each, the sidecar (cached geospatial metadata) + a HEAD give size + mtime
- Rows sort newest-first; a delete row action opens an AlertDialog → `DELETE /layers/{id}`

## Edge Cases
- No layers → empty state with a "New layer" CTA
- A bare COG dropped under the prefix with no sidecar → the service rebuilds the sidecar from the COG on demand (`_ensure_sidecar`)

## UX States
- Empty / Loading (skeleton) / Error (`ErrorState` + retry) / populated table

## Verification
- Test files: `services/api/tests/test_layers.py`
- Required cases: list returns summaries; delete returns `{deleted, id}` and 404s a missing layer
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [File Browser](file-browser.md) — the untouched full-bucket explorer
- [Map Viewer](map-viewer.md)
- [App Workflows](../app-workflows.md)
