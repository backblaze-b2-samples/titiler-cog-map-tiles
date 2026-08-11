import { describe, expect, it } from "vitest";
import type { RenderConfig } from "@titiler-cog-map-tiles/shared";

import { renderQuery, tileUrl } from "@/lib/layer-render";

const single: RenderConfig = {
  band_preset: "single",
  colormap: "terrain",
  rescale_min: 0,
  rescale_max: 500,
  resampling: "nearest",
  bidx: 1,
};

const rgb: RenderConfig = {
  band_preset: "rgb",
  colormap: "viridis",
  rescale_min: null,
  rescale_max: null,
  resampling: "bilinear",
  bidx: 1,
};

describe("renderQuery", () => {
  it("single-band carries colormap, rescale, and band index", () => {
    const query = renderQuery(single);
    expect(query).toContain("colormap_name=terrain");
    expect(query).toContain("rescale=0%2C500");
    expect(query).toContain("bidx=1");
    expect(query).toContain("resampling=nearest");
  });

  it("rgb omits colormap and rescale (renders natively)", () => {
    const query = renderQuery(rgb);
    expect(query).not.toContain("colormap_name");
    expect(query).not.toContain("rescale");
    expect(query).toContain("resampling=bilinear");
  });

  it("single-band without a rescale still emits the colormap", () => {
    const query = renderQuery({ ...single, rescale_min: null, rescale_max: null });
    expect(query).toContain("colormap_name=terrain");
    expect(query).not.toContain("rescale=");
  });
});

describe("tileUrl", () => {
  it("appends render params after ?layer= with &, keeping {z}/{x}/{y}", () => {
    const url = tileUrl(
      "/tiler/tiles/WebMercatorQuad/{z}/{x}/{y}.png?layer=abc",
      single,
      "http://api"
    );
    expect(url).toContain("http://api/tiler/tiles/WebMercatorQuad/{z}/{x}/{y}.png?layer=abc&");
    expect(url).toContain("colormap_name=terrain");
    expect(url).toContain("{z}/{x}/{y}");
  });
});
