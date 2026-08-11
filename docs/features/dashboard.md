<!-- last_verified: 2026-08-11 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance view of the geospatial archive: how many COG layers exist,
how many raster bytes they occupy in B2, their total megapixels, and how many
tiles have been served.

## Used By
- UI: `/` (dashboard) — stat cards + recent layers + a "How it works" card
- API: `GET /layers/stats`, `GET /layers`

## Core Functions
- `services/api/app/service/layers.py` — `get_stats()` (layer count, total COG bytes, total megapixels from sidecar dimensions, `tiles_served`)
- `services/api/app/repo/layer_store.py` — `total_cog_bytes()`, `list_layer_ids()`
- `services/api/app/repo/counter.py` — `get_tiles_served()`
- `apps/web/src/components/dashboard/stats-cards.tsx` — the four metric cards (`useLayerStats`)
- `apps/web/src/components/dashboard/recent-layers-table.tsx` — the recent layers list

## Canonical Files
- Stats service: `services/api/app/service/layers.py`
- Stat cards: `apps/web/src/components/dashboard/stats-cards.tsx`

## Inputs
- None

## Outputs
- `LayerStats`: `layer_count`, `total_bytes` (+ human), `total_megapixels`, `tiles_served`

## Flow
- `GET /layers/stats` sums the COG object sizes under the sample prefix, adds up
  `width × height` from each sidecar for megapixels, counts layers, and reads the
  durable tiles-served counter
- The dashboard renders the four cards + a recent-layers table

## Edge Cases
- No layers → cards show 0 / "0 B" / 0.0 / tiles served so far
- B2 unreachable → `ErrorState` inline (never a misleading "0 layers")

## UX States
- Loading (skeletons + a LoadingNotice) / Error / populated

## Verification
- Test files: `services/api/tests/test_layers.py`
- Required cases: `GET /layers/stats` returns the five metrics
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Layer Library](layer-library.md)
- [Tile Serving](tile-serving.md)
- [App Workflows](../app-workflows.md)
