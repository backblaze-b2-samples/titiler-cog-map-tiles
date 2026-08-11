<!-- last_verified: 2026-08-11 -->
# Feature: File Browser

## Purpose
The **full-bucket** explorer kept unchanged from the starter kit: `/files` lists,
previews, downloads, and deletes any object in the B2 bucket. It is a starter
contract surface and is intentionally NOT modified by this sample.

For browsing this sample's own COG layers (scoped to the sample prefix), use the
**[Layer Library](layer-library.md)** at `/layers` instead — it sits alongside
`/files`.

## Used By
- UI: `/files` page and `apps/web/src/components/files/**`
- API: `GET /files`, `GET /files/{key}`, `GET /files/{key}/download`, `GET /files/{key}/preview`, `DELETE /files/{key}` (and the `/files-by-key/*` variants)

## Core Functions
- `services/api/app/service/files.py` — listing, presigned URLs, deletion
- `services/api/app/repo/b2_client.py` — B2 S3 access
- `apps/web/src/components/files/file-browser.tsx` — the tree browser

## Canonical Files
- Browser UI: `apps/web/src/components/files/file-browser.tsx`
- Files service: `services/api/app/service/files.py`

## Inputs
- Optional `prefix` and `limit` query params

## Outputs
- `FileMetadata[]`; presigned URLs for download/preview

## Flow
- Browser → `GET /files` → service lists the bucket via the shared listing cache → tree view
- Preview/download use short-lived presigned URLs

## Edge Cases
- Path-traversal keys rejected; large objects size-guarded for detailed metadata
- (See the starter's validation split — unchanged here)

## UX States
- Empty / Loading / Error / populated tree with hover actions

## Verification
- Test files: the starter's `services/api/tests/test_file_*`, `test_list_*`, `test_delete.py`
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: `pnpm verify` green

## Related Docs
- [Layer Library](layer-library.md) — the sample-scoped explorer
- [App Workflows](../app-workflows.md)
