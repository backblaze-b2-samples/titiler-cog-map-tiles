"""Layer management routes — service layer mocked, so these stay hermetic.

Covers the five UI verbs' backend contract (list/read/create/update/delete plus
the generate-sample and stats endpoints) and the error mapping to HTTP codes.
"""

from datetime import UTC, datetime

from app.service.layers import LayerError, LayerNotFound
from app.types import LayerDetail, LayerStats, LayerSummary, RenderConfig


def _detail(layer_id: str = "abc123") -> LayerDetail:
    return LayerDetail(
        id=layer_id,
        name="SF Elevation",
        size_bytes=2048,
        size_human="2.0 KB",
        band_count=1,
        dtype="float32",
        minzoom=11,
        maxzoom=13,
        bounds=[-122.52, 37.70, -122.36, 37.83],
        uploaded_at=datetime.now(UTC),
        center=[-122.44, 37.76, 11],
        width=1024,
        height=1024,
        overview_levels=1,
        colorinterp=["gray"],
        render=RenderConfig(rescale_min=10.0, rescale_max=900.0),
        tiles="/tiler/tiles/WebMercatorQuad/{z}/{x}/{y}.png?layer=abc123",
    )


def _summary(layer_id: str = "abc123") -> LayerSummary:
    return LayerSummary(**{k: v for k, v in _detail(layer_id).model_dump().items()
                           if k in LayerSummary.model_fields})


async def test_list_layers(client, monkeypatch):
    monkeypatch.setattr("app.runtime.layers.list_layers", lambda: [_summary()])
    res = await client.get("/layers")
    assert res.status_code == 200
    body = res.json()
    assert body[0]["id"] == "abc123"
    assert body[0]["name"] == "SF Elevation"


async def test_get_layer_returns_detail_with_tile_template(client, monkeypatch):
    monkeypatch.setattr("app.runtime.layers.get_layer", lambda _id: _detail(_id))
    res = await client.get("/layers/abc123")
    assert res.status_code == 200
    body = res.json()
    assert body["tiles"] == "/tiler/tiles/WebMercatorQuad/{z}/{x}/{y}.png?layer=abc123"
    assert body["render"]["rescale_min"] == 10.0
    assert body["colormaps"] and "terrain" in body["colormaps"]


async def test_get_missing_layer_is_404(client, monkeypatch):
    def _raise(_id):
        raise LayerNotFound()

    monkeypatch.setattr("app.runtime.layers.get_layer", _raise)
    res = await client.get("/layers/does-not-exist")
    assert res.status_code == 404


async def test_generate_sample_layer(client, monkeypatch):
    seen = {}

    def _gen(name, kind, colormap=None, band_preset=None):
        seen["name"], seen["kind"] = name, kind
        return _detail()

    monkeypatch.setattr("app.runtime.layers.generate_sample_layer", _gen)
    res = await client.post("/layers/generate", json={"name": "My DEM", "kind": "elevation"})
    assert res.status_code == 201
    assert seen == {"name": "My DEM", "kind": "elevation"}


async def test_update_layer_renders_new_config(client, monkeypatch):
    captured = {}

    def _update(layer_id, name, render):
        captured["id"], captured["name"], captured["render"] = layer_id, name, render
        return _detail(layer_id)

    monkeypatch.setattr("app.runtime.layers.update_layer", _update)
    res = await client.patch(
        "/layers/abc123",
        json={
            "name": "Renamed",
            "render": {
                "band_preset": "single",
                "colormap": "magma",
                "rescale_min": 0,
                "rescale_max": 500,
                "resampling": "bilinear",
                "bidx": 1,
            },
        },
    )
    assert res.status_code == 200
    assert captured["name"] == "Renamed"
    assert captured["render"].colormap == "magma"


async def test_delete_layer(client, monkeypatch):
    calls = []
    monkeypatch.setattr("app.runtime.layers.remove_layer", lambda _id: calls.append(_id))
    res = await client.delete("/layers/abc123")
    assert res.status_code == 200
    assert res.json() == {"deleted": True, "id": "abc123"}
    assert calls == ["abc123"]


async def test_delete_missing_layer_is_404(client, monkeypatch):
    def _raise(_id):
        raise LayerNotFound()

    monkeypatch.setattr("app.runtime.layers.remove_layer", _raise)
    res = await client.delete("/layers/nope")
    assert res.status_code == 404


async def test_create_layer_rejects_bad_geotiff(client, monkeypatch):
    def _raise(name, data, resampling, colormap=None, band_preset=None):
        raise LayerError("GeoTIFF has no CRS", status_code=422)

    monkeypatch.setattr("app.runtime.layers.create_layer_from_upload", _raise)
    res = await client.post(
        "/layers",
        files={"file": ("bad.tif", b"not a tiff", "image/tiff")},
        data={"name": "x", "resampling": "nearest"},
    )
    assert res.status_code == 422


async def test_layer_stats(client, monkeypatch):
    stats = LayerStats(
        layer_count=3,
        total_bytes=1500,
        total_bytes_human="1.5 KB",
        total_megapixels=12.5,
        tiles_served=42,
    )
    monkeypatch.setattr("app.runtime.layers.get_stats", lambda: stats)
    res = await client.get("/layers/stats")
    assert res.status_code == 200
    assert res.json()["tiles_served"] == 42
    assert res.json()["layer_count"] == 3
