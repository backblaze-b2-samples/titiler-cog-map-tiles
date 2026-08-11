"""The mounted tiler's path dependency is the SSRF gate: it must only ever
resolve a validated layer id to a path INSIDE the sample prefix, never an
arbitrary url."""

import pytest
from fastapi import HTTPException

from app.config import settings
from app.runtime.tiler import layer_path_dependency


@pytest.mark.parametrize(
    "bad",
    [
        "../secret",
        "a/b",
        "http://evil.example/x.tif",
        "s3://other-bucket/x.tif",
        "",
        "x" * 200,
        "has space",
        ".hidden",
    ],
)
def test_rejects_ids_outside_the_safe_shape(bad):
    with pytest.raises(HTTPException) as exc:
        layer_path_dependency(bad)
    assert exc.value.status_code == 400


def test_accepts_valid_id_and_scopes_to_the_sample_prefix(monkeypatch):
    monkeypatch.setattr(settings, "b2_bucket_name", "my-bucket")
    url = layer_path_dependency("abc123DEF-_")
    assert url == "s3://my-bucket/titiler-cog-map-tiles/layers/abc123DEF-_.tif"
    assert settings.sample_prefix in url
