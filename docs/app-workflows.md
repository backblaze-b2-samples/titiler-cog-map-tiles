<!-- last_verified: 2026-08-11 -->
# App Workflows

User journeys inside the application. The primary entity is the **Layer** (one
COG in B2 + a render-config sidecar); all five verbs are in the UI.

## Create a layer (create)

- User navigates to `/layers/new`
- Picks a **source** (a RadioGroup, not free text): "Generate sample layer"
  (default — works with zero data or key) or "Upload GeoTIFF"
- Names the layer (`e.g. sf-elevation`) and optionally sets render defaults
  (colormap Select, band-preset RadioGroup — both default to "Auto (from raster)")
- **Generate**: `POST /layers/generate` builds a synthetic, georeferenced COG
  server-side (San Francisco bbox) and stores it in B2
- **Upload**: the chosen GeoTIFF is sent to `POST /layers`, converted to a valid
  COG with internal overviews (rio-cogeo), and stored in B2. A raster with no CRS
  is rejected with a clear message
- On success: a toast, and the app navigates to the new layer's detail page
- See: [COG Ingest](features/cog-ingest.md)

## Browse the layer library (read)

- User navigates to `/layers`
- The table lists every COG in the sample prefix with name, bands, dtype, zoom
  range, and size (newest first)
- A row links to the layer's detail; a row action deletes it
- Empty state offers a "New layer" CTA
- See: [Layer Library](features/layer-library.md)

## View a layer on the map (run)

- User opens `/layers/[id]`
- A Leaflet map (keyless OSM base) centers on the layer's real-world bounds and
  overlays the COG's tiles, rendered on demand by TiTiler straight from B2
- The "Live render" controls re-tune the view instantly by changing the tile URL:
  band preset (RadioGroup), colormap (Select), rescale min/max (numeric), and
  resampling (Select). This map + controls ARE the run verb — nothing is
  pre-rendered
- A "COG info" panel shows bounds, bands, dtype, dimensions, megapixels,
  overviews, and zoom range
- See: [Map Viewer](features/map-viewer.md), [Tile Serving](features/tile-serving.md)

## Edit a layer's render settings (edit)

- On `/layers/[id]`, "Edit" opens a dialog **pre-filled** from the layer's sidecar
- The user renames the layer and changes its default render config, then saves
- `PATCH /layers/{id}` rewrites the sidecar JSON; the detail refreshes
- See: [Map Viewer](features/map-viewer.md)

## Delete a layer (delete)

- From a library row or the detail page, "Delete" opens an AlertDialog confirm
- Confirming calls `DELETE /layers/{id}`, which removes the COG **and** its sidecar
  from B2 (scoped to the sample prefix), then the row/page updates

## Browse the full bucket (kept from the starter)

- User navigates to `/files`
- Page loads the 100 most recent objects from the API (sorted most recent first). While it loads, the page says so on screen and escalates the wording if the wait runs long — a full bucket listing measured 2.8s-21s cold
- If that limit was hit, a notice states how many objects the bucket actually holds — the page never claims to show everything
- Files displayed in tree view with folders and type-specific icons
- Folders auto-expand on load until the *majority* of the listed files are reachable without clicking, so the page's own "click a file" instruction is always actionable. Stopping at the first visible file was not enough: one stray top-level object left the other 99 sealed in collapsed folders while the page claimed to show 100
- Clicking a file row opens its preview; the per-row actions menu (preview / download / delete) is always visible, on every viewport
- Arriving at `/files?preview=<key>` expands that file's folders and opens its preview directly. This is how the ⌘K palette and the dashboard's recent-uploads rows hand off a *specific* file; the param is consumed on arrival so it doesn't re-fire later
- **Preview**: opens dialog with image/PDF preview + metadata panel, and the file's Download / Delete actions — the advertised "click a file" path offers everything the row menu does. The loading state holds until the media paints; a failure offers "Open in a new tab". The preview URL is signed with `Content-Disposition: inline` so PDFs render in place
- **Download**: shows a pending state on the row plus a toast while the presigned URL is fetched, then starts the download via an anchor click (which, unlike a popup, still works if the click's user activation expired during a slow presign). Failures are reported; the click can never silently do nothing
- **Delete**: the confirmation dialog stays open showing "Deleting..." until the request settles, then the row disappears with the toast (optimistic cache update) and the list reconciles with the server. The dialog is held deliberately — Radix closes on action click by default, which dismissed the only pending state and left the row looking untouched while the delete was still in flight
- Empty bucket shows "No files found" with upload prompt
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Stat cards show geospatial metrics: number of COG layers, total raster bytes in
  B2, total megapixels, and tiles served
- A recent-layers table links each layer to its detail page
- A "How it works" card explains the COG-on-B2 + TiTiler pattern
- Empty state: prompts to create the first layer
- See: [Dashboard](features/dashboard.md)

## Change Preferences

- User navigates to `/settings`
- A banner at the top states that the page is mostly a demonstration: only Theme is wired up for real, the rest showcases what a settings page can look like when you adapt the kit
- **Theme** (real): editing it and saving applies it immediately and persists it (`next-themes`), and the header's theme toggle drives the same state
- **Profile and preference fields** (demo): Display name, Bio, Default file view (Tree/List/Grid), Email me on every upload, Warn me when approaching quota + threshold. Each is labelled "Demo field", persists to `localStorage` only, and drives no behaviour — there is no account system, mailer, quota banner, activity log, or List/Grid view behind them yet
- Saving reports honestly: a success toast that separates the real theme change from the locally-stored demo values, or a warning toast if the browser blocked storage (theme still changes). It never claims a save that did not happen — the original page toasted "Settings saved" for fields that changed nothing
- Danger Zone actions are a demo — no real delete runs
- See: [Settings](features/settings.md)
