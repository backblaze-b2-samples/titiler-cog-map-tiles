import type { RenderConfig } from "@titiler-cog-map-tiles/shared";

import { API_BASE } from "@/lib/api-client";

/**
 * TiTiler query params for a render config. RGB layers render natively (no
 * colormap/rescale); single-band layers carry a named colormap, an optional
 * rescale, and the band index. Kept a pure function so the map viewer can
 * re-tune a layer live by rebuilding the tile URL — no server round-trip.
 */
export function renderQuery(render: RenderConfig): string {
  const params = new URLSearchParams();
  if (render.band_preset === "single") {
    params.set("colormap_name", render.colormap);
    if (render.rescale_min !== null && render.rescale_max !== null) {
      params.set("rescale", `${render.rescale_min},${render.rescale_max}`);
    }
    params.set("bidx", String(render.bidx));
  }
  params.set("resampling", render.resampling);
  return params.toString();
}

/**
 * Full XYZ tile URL template for Leaflet. Combines the layer's app-relative
 * `tiles` template (which already carries `?layer=<id>` and the literal
 * `{z}/{x}/{y}` placeholders Leaflet substitutes) with the render params and
 * the API origin.
 */
export function tileUrl(
  tilesTemplate: string,
  render: RenderConfig,
  apiBase: string = API_BASE
): string {
  const query = renderQuery(render);
  const separator = tilesTemplate.includes("?") ? "&" : "?";
  return `${apiBase}${tilesTemplate}${query ? `${separator}${query}` : ""}`;
}
