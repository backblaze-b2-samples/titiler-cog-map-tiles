"""OpenAPI contract freshness checks."""

import sys
from pathlib import Path

from main import app

# The exporter owns the target path and the JSON rendering format. Importing
# both (instead of re-deriving them here) keeps this test and
# `pnpm contract:export` from disagreeing about what "current" means: changing
# the rendering would otherwise fail this test on a freshly exported file.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from export_openapi import DEFAULT_TARGET, STALE_HINT, render_contract  # noqa: E402

CONTRACT_PATH = DEFAULT_TARGET


def test_checked_in_openapi_contract_is_current():
    # Existence is asserted first so a missing artifact reports the fix
    # instead of a bare FileNotFoundError from read_text().
    assert CONTRACT_PATH.exists(), f"{CONTRACT_PATH} is missing. {STALE_HINT}"

    expected = render_contract(app.openapi())

    assert CONTRACT_PATH.read_text(encoding="utf-8") == expected, (
        f"{CONTRACT_PATH} is stale. {STALE_HINT}"
    )


def test_openapi_metadata_uses_canonical_local_api_identity():
    schema = app.openapi()

    assert schema["info"] == {
        "title": "TiTiler COG Map Tiles API",
        "description": (
            "Local API for TiTiler COG Map Tiles: manage Cloud-Optimized "
            "GeoTIFF map layers stored in Backblaze B2 and serve dynamic XYZ "
            "tiles read straight from B2 by TiTiler. This contract documents "
            "the sample's own management API; the mounted TiTiler tile sub-app "
            "has its own schema and is not part of this contract."
        ),
        "version": "0.1.0",
    }
