"""Seed the B2 bucket with synthetic sample COG layers (keyless, reproducible).

Generates one of each sample kind (a single-band "elevation" surface and a
3-band RGB pattern), both georeferenced over a real bbox (San Francisco), and
uploads them to the sample prefix as valid COGs with internal overviews — the
same path the "Generate sample layer" UI action uses. No external download, no
second key: only your B2 credentials from the repo-root .env.

Usage:
    python services/api/scripts/seed_sample_cog.py
    python services/api/scripts/seed_sample_cog.py --kind elevation --name sf-dem
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Load the repo-root .env exactly like the app, then apply GDAL config.
from dotenv import load_dotenv

API_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(API_ROOT.parent.parent / ".env")
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.repo import SAMPLE_KINDS  # noqa: E402
from app.repo.gdal_s3 import configure_gdal_s3  # noqa: E402
from app.service.layers import generate_sample_layer  # noqa: E402

DEFAULT_NAMES = {"elevation": "SF Elevation (sample)", "rgb": "SF RGB (sample)"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kind",
        choices=list(SAMPLE_KINDS),
        help="Only seed this kind (default: one of each).",
    )
    parser.add_argument("--name", help="Layer name (only with --kind).")
    args = parser.parse_args()

    configure_gdal_s3()
    kinds = [args.kind] if args.kind else list(SAMPLE_KINDS)
    for kind in kinds:
        name = args.name if (args.kind and args.name) else DEFAULT_NAMES[kind]
        layer = generate_sample_layer(name, kind)
        sys.stdout.write(f"Seeded {kind} layer '{layer.name}' -> id={layer.id}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
