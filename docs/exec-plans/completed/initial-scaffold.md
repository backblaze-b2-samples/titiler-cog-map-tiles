# Plan — `titiler-cog-map-tiles`

Scaffold a new B2 sample from **vibe-coding-starter-kit** (source of truth:
`.claude/scratch/vcsk-74d349a0-7247-44c5-ba1e-4ab2386e847e/`). Built tree lands at
`./titiler-cog-map-tiles`.

---

## 1. Purpose

`titiler-cog-map-tiles` is a full-stack sample for **geospatial platform teams and
mapping-application developers** who want to store massive Cloud-Optimized GeoTIFF
(COG) rasters — satellite scenes, aerial orthomosaics, elevation grids — **directly
in Backblaze B2** and serve dynamic, resolution-appropriate **XYZ map tiles** to
browser/mobile clients **without an intermediate tile server holding a copy of the
data**. [TiTiler](https://github.com/developmentseed/titiler) (FastAPI + rio-tiler +
GDAL) reads only the COG byte-ranges it needs from B2 over the **S3-compatible API**
and renders each tile on demand. The app demonstrates the full lifecycle of a COG
map **Layer**: ingest a raster (converted to COG and uploaded to B2), browse the
layer library, tune its render settings, view it live on an interactive Leaflet map,
and delete it — all with **B2 credentials only, no second API key, no external
model, no GPU**. B2 is the star: it is the durable, range-readable storage layer
that lets one growing archive (50–500 GB per mission) be served directly, with zero
data duplication.

---

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is a Next.js 16 / React 19 web app + FastAPI backend with a strict
layered architecture (`types → config → repo → service → runtime`), an OpenAPI
contract test, and `check:agent-docs` drift gates. **The starter is the ceiling —
strip what this app doesn't need; do not rebuild what it ships.** Respect the
starter-contract "keep as-is" list in `AGENTS.md` §2 (UI kit, `/files` explorer,
`/upload`, sidebar nav).

| KEEP (as-is) | TRIM (remove from starter) | ADD (new for this sample) |
|---|---|---|
| `apps/web/src/components/ui/**` (shadcn primitives), `globals.css` tokens, `/design` page | — (do not touch the UI kit) | — |
| **`/files` full-bucket explorer** (`app/files/`, `components/files/`) — **NON-NEGOTIABLE KEEP** (starter contract) | — | **Sample-scoped asset explorer:** a **`/layers`** view — the COG **Layer library** scoped to the sample's own B2 prefix (`titiler-cog-map-tiles/layers/`). This is the required sample-specific explorer that sits *alongside* the untouched full-bucket `/files`. |
| `/upload` route + `components/upload/**` (generic file upload → B2) | — | A dedicated **COG ingest** path (`/layers/new`) that converts an uploaded GeoTIFF to COG server-side (rio-cogeo) then stores it in B2. Generic `/upload` stays for the bucket explorer. |
| Backend layering, middleware order, health/metrics/ratelimit runtime, list-cache, `repo/b2_client.py` (boto3 S3 adapter, already sets `user_agent_extra`) | — | `repo/cog_reader.py` (rio-tiler COG open/info/validate + GDAL-S3 env), `repo/gdal_s3.py` (apply GDAL VSI-S3 config from `B2_*` at startup), `repo/layer_store.py` (list/read/write per-layer sidecar JSON), `service/layers.py`, `runtime/layers.py` (management contract endpoints), and a **mounted TiTiler sub-app** for image tiles. |
| TanStack Query data layer (`lib/queries.ts`, `lib/api-client.ts`), API contract test harness | Starter's upload-centric dashboard **aggregations** (replace, don't delete the plumbing) | `queries.ts` hooks for layers CRUD + layer info; new `API_CLIENT_ROUTES` entries for the management endpoints. |
| `/settings` page (theme is real; rest is honest demo) + `settings-form.tsx` (form-UX exemplar) | — | Keep as-is; it is the exemplar the Layer create/edit forms copy. |
| Dashboard **plumbing** (`stats-cards`, `upload-chart`, `queries`) via the same `runtime→service→repo` layering | Upload-oriented **copy/metrics** on `/` (files uploaded, upload activity) | **Adapt** dashboard to geospatial metrics: # of COG layers, total raster bytes in B2, total megapixels, **tiles served** (durable counter). |
| `infra/vercel`, `infra/railway`, CI (`ci.yml`), agent-docs scripts | — | Adjust only for the new deps / branding (see §6). |
| `scripts/setup_b2_cors.py` | — | Rename env vars only (S3-only; still useful, low priority — tiles are `<img>` so not CORS-gated). |

**Bucket-explorer tension note:** none — the full-bucket `/files` explorer is kept
untouched, and the sample-specific `/layers` explorer is *added* beside it, exactly
as the contract requires.

---

## 3. B2 surface (all S3-compatible — **no b2-native API**)

Two S3 access paths, **both S3-compatible, both carrying the same custom UA token**:

1. **Management path — boto3** (`repo/b2_client.py`, already present; keep):
   `put_object` (store COG + sidecar JSON), `list_objects_v2` (layer library +
   full-bucket explorer + stats), `head_object` (metadata), `delete_object`,
   `generate_presigned_url` (downloads). Already sets
   `Config(user_agent_extra=<token>)`. ✅ Standard #2.
2. **Tile-read path — GDAL / rio-tiler (TiTiler)**: reads COG byte-ranges from
   `s3://<bucket>/<key>` via GDAL's `/vsis3/` virtual filesystem. This is the
   S3 Range-GET pattern that makes COG-from-object-storage work. **Custom UA is set
   on this path via the GDAL env var `GDAL_HTTP_USERAGENT=<same token>`** — GDAL has
   no boto3 client, so its UA mechanism is an env var (analogous to the DuckDB
   `http_agent` / PyArrow cases). Record this so the reviewer / `b2-doctor` does not
   false-flag the GDAL path as "missing user agent": it satisfies Standard #2 by the
   only means GDAL offers.

   Required GDAL/VSI-S3 config (applied at startup in `repo/gdal_s3.py`, derived from
   `B2_*`; set into `os.environ` **before** rasterio is first used, or via a process
   default `rasterio.Env`):
   - `AWS_S3_ENDPOINT` = endpoint **host only, no scheme** (e.g. `s3.us-west-005.backblazeb2.com`)
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` = the `B2_*` key pair
   - `AWS_VIRTUAL_HOSTING=FALSE` (B2 needs **path-style**), `AWS_HTTPS=YES`, `AWS_REGION=<B2_REGION>`
   - `GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR` (critical — stops directory probes per open)
   - `CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif,.tiff`
   - `GDAL_HTTP_MERGE_CONSECUTIVE_RANGES=YES`, `GDAL_HTTP_MULTIPLEX=YES`, `VSI_CACHE=TRUE`, `VSI_CACHE_SIZE=536870912`
   - `GDAL_HTTP_USERAGENT=<b2 attribution token>`

**b2-native flags:** none. Justification: not applicable — everything is S3.

**Attribution token:** one token everywhere — boto3 `user_agent_extra`, GDAL
`GDAL_HTTP_USERAGENT`, and every Backblaze link's `utm_content`. Use **`b2ai-titiler-cog`**
(the starter's `b2ai-oss-start` is replaced by this single value; `check:agent-docs`
`branding.mjs` enforces the one-token rule).

---

## 4. Key features

Primary entity = **Layer** (a COG map layer: one COG object in B2 +
a small render-config/display sidecar JSON). Stored under the sample prefix
`titiler-cog-map-tiles/layers/<id>.tif` and `.../<id>.json`.

1. **Ingest a COG layer** — upload a GeoTIFF through the API; the server validates
   it, converts to a valid COG **with internal overviews** via `rio-cogeo`
   (`cog_translate`), and `put_object`s it to B2. Also a **"Generate sample layer"**
   action that runs the bundled synthetic-COG generator server-side so the demo
   works with zero user-supplied data. *(deployment: **local** — CPU only; COG
   translation is CPU raster work, there is no GPU path at all. No external provider,
   no key, ~$0.)*
2. **Dynamic XYZ tile serving from B2** — TiTiler reads COG byte-ranges from B2 and
   renders tiles on demand at the requested z/x/y, band combination, colormap, and
   rescale. No pre-rendered tile pyramid on a server; B2 is the only copy.
   *(deployment: **local** — TiTiler/GDAL run in-process, CPU, no key, ~$0.)*
3. **Interactive map viewer** — a Leaflet map (keyless OSM base tiles) overlays the
   selected layer's tiles, centered on the layer's real-world bounds; live controls
   re-tune band/colormap/rescale by changing the tile URL query params.
4. **Layer library (sample-scoped explorer)** — `/layers` lists every COG layer in
   the sample prefix with name, bounds, band count, dtype, min/max zoom, and size.
5. **Layer render settings (edit)** — rename a layer and change its default render
   config (band preset, colormap, rescale min/max), persisted to the sidecar JSON.
6. **Geospatial dashboard** — # of layers, total raster bytes in B2, total
   megapixels, and **tiles served** (durable counter incremented per tile request).

**External API provider:** none. Every feature is `deployment: local`, keyless,
CPU-only, ~$0/run. There is no ML model and no GPU code path (raster rendering is
CPU GDAL); the CPU-default/GPU-autodetect rule is satisfied trivially (CPU-only, no
accelerator branch). **Genblaze:** not applicable — the description names no
Genblaze / suggested AI stack.

**Primary-entity lifecycle (Layer) — all five verbs in the UI (no omissions):**

| Verb | UI surface |
|---|---|
| **create** | `/layers/new` — upload GeoTIFF → COG, **or** "Generate sample layer". Form below. |
| **read** | `/layers` library list + `/layers/[id]` detail with the map viewer. |
| **edit** | `/layers/[id]` "Edit" — rename + change render config (opens pre-filled). |
| **delete** | `/layers/[id]` (and row action) — AlertDialog confirm → deletes COG + sidecar from B2 (scoped to the sample prefix). |
| **run** | "View on map" (`/layers/[id]`) — renders live XYZ tiles from B2 via TiTiler; the map + live render controls ARE the run verb. |

`omitted_ui_verbs`: **empty** — every verb the app supports is built in the UI.

**Form UX conventions:**
- *Selector (finite-value) fields — create AND edit:* **colormap** (Select — e.g.
  viridis / terrain / greys / rdylgn…), **band preset** (RadioGroup — e.g. "RGB",
  "Single band + colormap"), **resampling** (Select — nearest / bilinear / cubic),
  **source** on create (RadioGroup — "Upload GeoTIFF" / "Generate sample layer").
  Never free-text for these.
- *Free-text fields:* layer **name**; **rescale min/max** numeric inputs.
- *Create-form safe-default hints (guidance only, never an autofill button):*
  surface via `placeholder` / `FormDescription` — e.g. name placeholder
  `"e.g. sf-elevation"`, colormap default hint "terrain works well for elevation",
  band preset default "Single band + colormap", rescale hint "leave blank to
  auto-scale from the COG's min/max". Copy the exemplar pattern from
  `apps/web/src/components/settings/settings-form.tsx`.
- The **edit** form opens pre-filled from the layer's sidecar (no default hints
  needed — it edits a real resource).

---

## 5. Doc transforms

Under `docs/features/`:
- **Rewrite** `dashboard.md` → geospatial metrics (layers, raster bytes, megapixels,
  tiles served).
- **Rewrite** `file-upload.md` → `cog-ingest.md` (GeoTIFF→COG conversion + upload;
  the generate-sample path).
- **Rewrite** `file-browser.md` → keep a short note that `/files` is the untouched
  full-bucket explorer; point Layer-specific browsing at the new `layer-library.md`.
- **Rewrite** `metadata-extraction.md` → `cog-info.md` (bounds/bands/dtype/overviews/
  zoom range read via rio-tiler).
- **Keep** `settings.md` (theme-only-real demo, unchanged).
- **New stubs** (from `_template.md`): `tile-serving.md` (TiTiler + B2 range-reads,
  GDAL VSI-S3 config, the custom-UA-via-env note), `map-viewer.md` (Leaflet +
  react-leaflet@5 + keyless OSM base), `layer-library.md`.
- Update `ARCHITECTURE.md` (new repo/service/runtime modules + the mounted TiTiler
  sub-app + the two S3 access paths), `docs/app-workflows.md` (Layer lifecycle
  journeys), `README.md` (new purpose, quick start, feature list), and the
  `AGENTS.md`/shims + `scripts/check-agent-docs.mjs` registration if the agent-doc
  surface changes (keep the one-token branding rule green).
- Regenerate `docs/api/openapi.json` via `pnpm contract:export` after adding the
  management routes.

---

## 6. Rename table (`vibe-coding-starter-kit` → `titiler-cog-map-tiles`)

| Identifier / kind | From | To |
|---|---|---|
| kebab slug / repo / dir | `vibe-coding-starter-kit` | `titiler-cog-map-tiles` |
| Title Case display (`APP_NAME` in `lib/app-config.ts`) | `Vibe Coding Starter Kit` | `TiTiler COG Map Tiles` |
| `APP_DESCRIPTION` | file-management template blurb | `Serve dynamic XYZ map tiles from Cloud-Optimized GeoTIFFs stored in Backblaze B2` |
| FastAPI `API_TITLE`/description (`main.py`) | derives from `APP_NAME` | derives from new `APP_NAME` (keep the derive-from-`APP_NAME` link intact — `check:agent-docs` branding gate) |
| root `package.json` `name` | `vibe-coding-starter-kit` | `titiler-cog-map-tiles` |
| workspace pkg names (`@vcsk/*` if any) | `vibe-coding-starter-kit`-derived | `titiler-cog-map-tiles`-derived |
| **B2 attribution token** — boto3 `user_agent_extra` + GDAL `GDAL_HTTP_USERAGENT` + all `utm_content` | `b2ai-oss-start` | **`b2ai-titiler-cog`** (one value everywhere) |
| project-page / labs links | `.../projects/vibe-coding-starter-kit/` | `.../projects/titiler-cog-map-tiles/` |
| CI workflow / job names referencing the kit name | `vibe-coding-starter-kit` | `titiler-cog-map-tiles` |
| docker image tag / Railway/Vercel service names | starter values | `titiler-cog-map-tiles`-derived |

### Env-var standardization (Standard #3 — starter deviates; rename in the same pass)

The starter uses `B2_KEY_ID` + `B2_ENDPOINT` and no region/public-url-base. Rename to
the canonical `B2_*` set across `.env.example`, `settings.py`, `main.py`
(`REQUIRED_B2_SETTINGS` + placeholder set), `repo/b2_client.py`, `repo/gdal_s3.py`,
`scripts/setup_b2_cors.py`, tests, and all docs:

| From (starter) | To (Standard #3) |
|---|---|
| `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` |
| `B2_APPLICATION_KEY` | `B2_APPLICATION_KEY` (unchanged) |
| `B2_BUCKET_NAME` | `B2_BUCKET_NAME` (unchanged) |
| `B2_ENDPOINT` (full URL) | derive from **`B2_REGION`** (`https://s3.{B2_REGION}.backblazeb2.com`); keep an optional `B2_ENDPOINT` override |
| `b2_public_url` | `B2_PUBLIC_URL_BASE` |
| (none) | add **`B2_REGION`** |

GDAL needs the endpoint **host only** (strip the `https://`) for `AWS_S3_ENDPOINT`,
and `AWS_REGION` = `B2_REGION`.

---

## Build gotchas & non-obvious constraints (read before coding)

- **Python 3.12 baseline** (`python-runtime.mjs`, `.python-version`). All native
  wheels below have cp312 wheels; `rasterio` bundles GDAL in its wheel — **no system
  GDAL/PROJ install needed** on macOS arm64 or Linux.
- **Pin a mutually-compatible native set** and **regenerate `requirements.lock`**
  (`test_dependency_lock.py` enforces lock↔txt agreement; setup + CI install the
  lock). Add to `requirements.txt` (lower-bound `>=` pins only, per the file's
  contract): `titiler.core`, `rio-tiler`, `rasterio`, `rio-cogeo`, `numpy`. Choose a
  coherent set (e.g. `rasterio>=1.4` to allow `numpy>=2`, with `rio-tiler>=6` and a
  `titiler.core` that matches that `rio-tiler`; if you pin `rasterio<1.4` you MUST
  also pin `numpy<2`). **Unbounded/incoherent native pins are a false green** (boots +
  unit tests pass, tile render explodes on a clean install) — verify a real
  tile-render round-trip, not import-only.
- **react-leaflet@5** (v4 peer-requires React 18; the starter is React 19). Import
  the map **dynamically with `ssr: false`** (Leaflet touches `window`). Base tiles =
  **keyless OSM** (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`) with attribution.
  Add `leaflet` + `react-leaflet@^5` and import `leaflet/dist/leaflet.css`.
- **Mount TiTiler as a sub-app** (`app.mount("/tiler", tiler_app)`), NOT via
  `include_router` into the main app. Mounted sub-apps have their **own** OpenAPI, so
  TiTiler's ~15 routes stay **out of `docs/api/openapi.json`** and the contract test /
  `api-contract.test.ts` `SERVER_ONLY_OPERATIONS` list stay clean. The frontend
  consumes only **image tiles** from the sub-app via `<img>` (Leaflet `L.tileLayer`),
  which are **not CORS-gated**, so the sub-app needs no CORS middleware. All
  **metadata** the UI needs (bounds, bands, zoom range, render config) comes from our
  **own contract endpoints** (`runtime/layers.py`), which read the COG via rio-tiler
  in `repo/cog_reader.py`. This keeps layering + contract gates satisfied.
- **Constrain the tiler `url`** (SSRF safety): give the mounted tiler a
  `path_dependency` that maps a layer **id** → `s3://{bucket}/{prefix}/{id}.tif` and
  **rejects anything outside the sample prefix**. Never expose a raw arbitrary `?url=`.
- **Layering:** rio-tiler / GDAL config live in `repo/` (`cog_reader.py`,
  `gdal_s3.py`); `service/layers.py` holds logic; `runtime/layers.py` only routes.
  boto3 stays in `repo/` (structural test `test_boto3_only_in_repo`). Keep each
  authored `app/**` Python file **< 300 lines** (`test_api_app_python_file_size_limit`).
- **Synthetic, keyless, reproducible seed COGs** (`services/api/scripts/seed_sample_cog.py`
  or `scripts/`): with numpy + rasterio, write **properly georeferenced** rasters over
  a **real-world bbox** (so they overlay OSM at a recognizable place) — one 3-band
  raster and one single-band "elevation" raster with a smooth spatial signal — then
  `rio_cogeo.cog_translate` them into valid COGs **with internal overviews** (needed
  for multi-zoom tiles) and `put_object` to the sample prefix. No external download,
  no key. These must render as visually interesting tiles (the `sample-4-screenshot`
  step will capture the map).
- **Tiles-served counter:** reuse the starter's durable-counter pattern
  (`repo/counter.py`, `download_count_file`) → a `tiles_served` counter incremented by
  a tiny middleware/dependency on tile requests; surfaced on the dashboard. Keep the
  counter file **outside `services/api/`** (the starter comment explains the
  `--reload` watch-tree footgun).
- **Every route change** re-exports `docs/api/openapi.json` (`pnpm contract:export`)
  and updates `lib/api-client.ts` `API_CLIENT_ROUTES` + `lib/queries.ts`; run
  `pnpm verify` green before finishing.

**Verification bar:** `pnpm run setup` → `pnpm verify` green, and a real end-to-end
render: generate a sample layer → it lands in B2 under the sample prefix → `/layers`
lists it → the map viewer paints TiTiler tiles read from B2 (spot-check one
`/tiler/.../tiles/{z}/{x}/{y}` returns a real PNG). Do not accept import-only green.
