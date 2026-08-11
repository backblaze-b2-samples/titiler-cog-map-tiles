<!-- last_verified: 2026-08-11 -->
# Feature: Map Viewer

## Purpose
Show a layer live on an interactive Leaflet map, centered on its real-world
bounds, with keyless OpenStreetMap base tiles and controls that re-tune the COG
render (band preset, colormap, rescale, resampling) by changing the tile URL —
this map + its live controls are the **run** verb.

## Used By
- UI: `/layers/[id]` (the map + "Live render" controls)

## Core Functions
- `apps/web/src/components/layers/leaflet-map.tsx` — the react-leaflet map (`MapContainer`, OSM `TileLayer`, the COG overlay `TileLayer`, `fitBounds`)
- `apps/web/src/components/layers/layer-map.tsx` — loads the map via `next/dynamic` with `ssr: false` (Leaflet touches `window`)
- `apps/web/src/components/layers/render-controls.tsx` — live selectors + rescale inputs
- `apps/web/src/lib/layer-render.ts` — `renderQuery()` / `tileUrl()` build the tile URL from a render config
- `apps/web/src/components/layers/layer-detail.tsx` — wires the map, controls, edit, and delete

## Canonical Files
- Map: `apps/web/src/components/layers/leaflet-map.tsx`
- Tile URL builder: `apps/web/src/lib/layer-render.ts`

## Inputs
- The layer's `bounds`, `center`, `minzoom`/`maxzoom`, `tiles` template
- A `RenderConfig` (ephemeral, seeded from the layer's saved render)

## Outputs
- A painted map; the COG overlay `TileLayer` remounts (via `key`) when the tile URL changes, so re-tuning is instant

## Notes
- **react-leaflet@5** is used because v4 peer-requires React 18 while this app is on React 19.
- Base tiles are **keyless OSM** (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`) with attribution.
- The map reads image tiles from the mounted tiler via `<img>` (not CORS-gated); all metadata comes from the app's own `/layers` endpoints.

## Flow
- The detail page loads the layer via `useLayer(id)`
- `tileUrl(layer.tiles, render)` produces the COG overlay URL
- Changing a control updates the ephemeral render → new URL → the overlay reloads

## Edge Cases
- Server-side render would crash on Leaflet's `window` use → avoided by `ssr: false`
- Single-band vs RGB: RGB renders natively (no colormap/rescale); single-band carries `colormap_name` + optional `rescale`

## UX States
- Loading: a skeleton fills the map frame while Leaflet loads
- Error / not found: `ErrorState` with retry

## Verification
- Test files: `apps/web/src/lib/layer-render.test.ts`
- Required cases: single-band query carries colormap + rescale + bidx; RGB omits colormap/rescale; `tileUrl` appends params after `?layer=` with `&` and keeps `{z}/{x}/{y}`
- Focused verify command: `pnpm test:web`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green; live, the map paints COG tiles over OSM

## Related Docs
- [Tile Serving](tile-serving.md)
- [Layer Library](layer-library.md)
- [App Workflows](../app-workflows.md)
