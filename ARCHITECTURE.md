<!-- last_verified: 2026-08-06 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Geospatial dashboard (layers, raster bytes, megapixels, tiles served)
  - `/layers` COG **Layer** library (sample-scoped) + create / detail pages
  - Interactive Leaflet map viewer (react-leaflet@5, keyless OSM base tiles)
  - The untouched full-bucket `/files` explorer and `/upload` from the starter
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - Layer management REST API (create/read/update/delete + generate + stats)
  - **Two S3 access paths to B2** (both S3-compatible, same UA token):
    boto3 for storage (`repo/b2_client.py`, `repo/layer_store.py`) and
    GDAL/rio-tiler for COG Range-GETs (`repo/gdal_s3.py`, `repo/cog_reader.py`)
  - GeoTIFF → COG conversion with internal overviews (`repo/cog_build.py`,
    rio-cogeo) and a synthetic seed generator (`repo/cog_seed.py`)
  - A **mounted TiTiler sub-app** at `/tiler` for on-demand XYZ tiles
  - Health, structured JSON logging, and Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (incl. the Layer models)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration,
                           mounts the TiTiler sub-app, applies GDAL/VSI-S3 config
  app/
    types/                 Pydantic models (layers.py, files.py, stats.py, …)
    config/                Settings loaded from environment (B2_* + sample prefix)
    repo/                  Data access:
                             b2_client.py / layer_store.py  (boto3 storage)
                             gdal_s3.py                     (GDAL VSI-S3 config)
                             cog_reader.py                  (rio-tiler info)
                             cog_build.py / cog_seed.py     (rio-cogeo translate)
                             counter.py                     (download + tiles counters)
    service/               Business logic (layers.py, files.py, upload.py)
    runtime/               FastAPI route handlers:
                             layers.py   (Layer management contract)
                             tiler.py     (mounted TiTiler sub-app + SSRF gate)
  scripts/                 export_openapi.py, setup_b2_cors.py
  tests/                   pytest tests (structural + integration + COG pipeline)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/list_cache.py`, the B2 connectivity cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`. The listing cache also owns the only background thread in the app: a stale entry is served immediately while that thread re-scans (stale-while-revalidate), and `main.lifespan` warms it once at startup so no user pays for the cold full-bucket scan.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repository: `web` builds from the
  repository root because it consumes `packages/shared`; `api` builds from
  `services/api`. The versioned per-service configs and the human-approved
  staging/production contract live in [infra/railway/README.md](infra/railway/README.md).
- **Vercel** — one project using [Vercel Services](https://vercel.com/docs/services):
  the `web` (Next.js) and `api` (FastAPI) services build from the same repo and
  share one origin — the web app at `/`, the API under `/api`. The repo-root
  `vercel.json` declares both services and routes `/api/*` to the API service;
  the Vercel-only `services/api/index.py` strips the `/api` prefix so FastAPI
  keeps its native paths (`/health`, `/files`, `/layers`, …). The kept `/upload`
  flow sends bytes directly from the browser to B2 via a presigned PUT, so it
  bypasses the Function's 4.5 MB payload ceiling (COG ingest via `POST /layers`,
  by contrast, is a server-side multipart translate — mind function size/timeout
  limits for large uploads). Map tiles are `<img>` requests and are not
  CORS-gated. A two-separate-Projects alternative and the full delivery contract
  live in [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## Two S3 access paths to B2

Both paths are S3-compatible (**no b2-native API**) and both carry the same
attribution token `b2ai-titiler-cog`:

1. **Management — boto3** (`repo/b2_client.py`, `repo/layer_store.py`): stores
   each layer's COG (`<prefix>layers/<id>.tif`) + a render-config sidecar
   (`<id>.json`), lists the library, HEADs, deletes, and presigns. Sets
   `Config(user_agent_extra="b2ai-titiler-cog")`.
2. **Tile reads — GDAL / rio-tiler** (`repo/gdal_s3.py`): TiTiler reads COG
   byte-ranges from `s3://<bucket>/<prefix>layers/<id>.tif` via GDAL's
   `/vsis3/`. GDAL has no boto3 client, so its custom user agent is set through
   `GDAL_HTTP_USERAGENT` — the only mechanism GDAL offers (analogous to the
   DuckDB `http_agent` / PyArrow cases). `configure_gdal_s3()` sets the VSI-S3
   env (`AWS_S3_ENDPOINT` host-only, path-style, `GDAL_DISABLE_READDIR_ON_OPEN`,
   range/merge tuning, the UA) from `B2_*` at startup, before rasterio's first
   open.

## Mounted TiTiler sub-app

TiTiler is mounted via `app.mount("/tiler", build_tiler_app())`, **not**
`include_router`. A mounted app has its own OpenAPI, so TiTiler's raster routes
stay out of `docs/api/openapi.json` and the contract tests. The browser reads
only image tiles from it (Leaflet `<img>` requests, not CORS-gated); all metadata
the UI needs comes from the app's own `/layers` endpoints. The tiler's
`path_dependency` accepts a validated `layer` id and maps it to a path **inside
the sample prefix**, rejecting anything else — it never exposes a raw `?url=`
(SSRF-safe). A tiny middleware increments the durable `tiles_served` counter on
each successful tile response.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API)
  - Layers live under the sample prefix `titiler-cog-map-tiles/layers/`: a COG
    `.tif` object plus a small render-config `.json` sidecar per layer
  - Listing/metadata via S3 `list_objects_v2` / `head_object`; COG geospatial
    metadata via rio-tiler over Range-GETs
  - No application database — B2 is the sole data store (durable counters persist
    to small local JSON files)

## External Services

- **Backblaze B2 S3 API** — COG + sidecar storage, listing, deletion, presigned
  URLs, and COG byte-range reads for tile rendering
- **OpenStreetMap tile server** — keyless base map tiles (`tile.openstreetmap.org`)

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

Layer lifecycle:

- **Create (upload)**: Browser -> `POST /layers` (multipart GeoTIFF) -> service
  `geotiff_to_cog` (rio-cogeo) -> read info from the in-memory COG -> `put_object`
  COG + sidecar to B2 -> `LayerDetail`
- **Create (generate)**: Browser -> `POST /layers/generate` -> `build_sample_cog`
  (numpy + rasterio + rio-cogeo, georeferenced over a real bbox) -> store in B2
- **Read**: `GET /layers` (library, from sidecars) and `GET /layers/{id}` (detail
  + tile template)
- **Run (tiles)**: Leaflet requests `GET /tiler/tiles/{tms}/{z}/{x}/{y}.png?layer=<id>&…`
  -> TiTiler reads COG Range-GETs from B2 via GDAL -> renders a PNG -> tiles_served++
- **Edit**: Browser -> `PATCH /layers/{id}` -> service rewrites the sidecar JSON
- **Delete**: Browser -> `DELETE /layers/{id}` -> repo deletes the COG + sidecar
  (scoped to the sample prefix)

The full-bucket `/files` explorer and `/upload` flows from the starter are kept
unchanged.

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

The frontend client keeps a small `API_CLIENT_ROUTES` registry in
`apps/web/src/lib/api-client.ts`. Tests compare that registry to the checked-in
OpenAPI artifact so route changes fail loudly before the hand-written client can
silently drift from FastAPI. `GET /metrics` is intentionally server-only.

## Canonical Files

- Layer routes (runtime): `services/api/app/runtime/layers.py`
- Mounted tiler + SSRF gate: `services/api/app/runtime/tiler.py`
- Layer service orchestration: `services/api/app/service/layers.py`
- B2 storage (repo): `services/api/app/repo/b2_client.py`, `repo/layer_store.py`
- GDAL VSI-S3 config (repo): `services/api/app/repo/gdal_s3.py`
- COG read / translate / seed (repo): `repo/cog_reader.py`, `repo/cog_build.py`, `repo/cog_seed.py`
- Pydantic models: `services/api/app/types/layers.py` (+ `files.py`, `stats.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- COG pipeline test: `services/api/tests/test_cog_pipeline.py`
- OpenAPI contract: `docs/api/openapi.json`
- Frontend API client / tile URL builder: `apps/web/src/lib/api-client.ts`, `lib/layer-render.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [COG Ingest](docs/features/cog-ingest.md)
- [Tile Serving](docs/features/tile-serving.md)
- [Map Viewer](docs/features/map-viewer.md)
- [Layer Library](docs/features/layer-library.md)
- [COG Info](docs/features/cog-info.md)
- [Dashboard](docs/features/dashboard.md)
- [File Browser](docs/features/file-browser.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
