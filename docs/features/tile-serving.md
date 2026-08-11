<!-- last_verified: 2026-08-11 -->
# Feature: Tile Serving

## Purpose
Serve dynamic XYZ map tiles from a COG **stored in B2**, rendered on demand — no
pre-rendered tile pyramid, no second copy of the data. TiTiler reads only the COG
byte-ranges it needs from B2 over the S3-compatible API and renders each tile at
the requested z/x/y, band combination, colormap, and rescale.

## Used By
- UI: the Leaflet overlay on `/layers/[id]` (image `<img>` tile requests)
- API: the mounted TiTiler sub-app at `/tiler/tiles/{tileMatrixSetId}/{z}/{x}/{y}.png?layer=<id>&…`

## Core Functions
- `services/api/app/runtime/tiler.py` — `build_tiler_app()` (TiTiler `TilerFactory` mounted as a sub-app), `layer_path_dependency()` (the SSRF gate), `tiles_served_middleware()`
- `services/api/app/repo/gdal_s3.py` — `configure_gdal_s3()` (GDAL VSI-S3 env from `B2_*`), `layer_s3_url()`
- `services/api/main.py` — `app.mount("/tiler", build_tiler_app())`
- `apps/web/src/lib/layer-render.ts` — `tileUrl()` builds the Leaflet tile URL from a render config

## Canonical Files
- Mounted tiler + SSRF gate: `services/api/app/runtime/tiler.py`
- GDAL VSI-S3 config: `services/api/app/repo/gdal_s3.py`

## Inputs
- `layer` id (validated, mapped to `s3://<bucket>/<prefix>layers/<id>.tif`)
- Render params: `colormap_name`, `rescale`, `resampling`, `bidx`

## Outputs
- A rendered PNG tile per request
- Side effect: the durable `tiles_served` counter increments on each 200

## Custom user agent via GDAL env (Standard #2)
GDAL has **no boto3 client**, so its custom user agent — required by the B2
standard — is set through the `GDAL_HTTP_USERAGENT` env var, the only mechanism
GDAL offers (analogous to the DuckDB `http_agent` / PyArrow cases). The value is
the **same** `b2ai-titiler-cog` token as the boto3 `user_agent_extra`. A reviewer
or `b2-doctor` should not flag the GDAL path as "missing user agent": it satisfies
Standard #2 by the only means GDAL provides.

## GDAL / VSI-S3 config (set at startup, from B2_*)
`AWS_S3_ENDPOINT` (host only), `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`,
`AWS_REGION`, `AWS_VIRTUAL_HOSTING=FALSE` (path-style), `AWS_HTTPS=YES`,
`GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR`, `CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif,.tiff`,
range/merge/multiplex tuning, `VSI_CACHE`, and `GDAL_HTTP_USERAGENT`.

## Flow
- Leaflet requests a tile URL for the current z/x/y and render config
- The tiler's `path_dependency` validates `layer` and maps it to the COG's s3 path
- TiTiler/GDAL fetch the COG byte-ranges from B2 (`/vsis3/`) and render the PNG
- The middleware increments `tiles_served`

## Edge Cases
- Invalid / out-of-prefix `layer` id → 400 (SSRF gate), never an arbitrary read
- Tile outside the COG bounds → 404 (rio-tiler error handlers), Leaflet ignores it
- Mounted sub-app has its own OpenAPI → tiler routes stay out of the app contract

## UX States
- The map shows the OSM base immediately; COG tiles paint as they render

## Verification
- Test files: `services/api/tests/test_tiler_security.py`, `services/api/tests/test_cog_pipeline.py`
- Required cases: SSRF gate rejects `../`, other buckets, and bad shapes while accepting a valid id scoped to the sample prefix; a seed COG renders a real PNG tile
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests green; live, a `/tiler/.../tiles/{z}/{x}/{y}.png` request returns a real PNG

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Map Viewer](map-viewer.md)
- [COG Ingest](cog-ingest.md)
- [App Workflows](../app-workflows.md)
