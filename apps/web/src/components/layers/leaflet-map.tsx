"use client";

// Leaflet touches `window`, so this component is only ever loaded via
// next/dynamic with `ssr: false` (see layer-map.tsx). react-leaflet@5 is used
// because v4 peer-requires React 18 and this app is on React 19.
import "leaflet/dist/leaflet.css";

import { useEffect } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";

export interface LeafletMapProps {
  /** [w, s, e, n] WGS84 */
  bounds: number[];
  /** [lng, lat, zoom] */
  center: number[];
  minzoom: number;
  maxzoom: number;
  /** Full XYZ tile URL for the COG overlay (already includes render params). */
  cogTileUrl: string;
}

function FitToLayer({ bounds }: { bounds: LatLngBoundsExpression }) {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(bounds, { padding: [16, 16] });
  }, [map, bounds]);
  return null;
}

export function LeafletMap({
  bounds,
  center,
  minzoom,
  maxzoom,
  cogTileUrl,
}: LeafletMapProps) {
  const [w, s, e, n] = bounds;
  const leafletBounds: LatLngBoundsExpression = [
    [s, w],
    [n, e],
  ];

  return (
    <MapContainer
      center={[center[1], center[0]]}
      zoom={center[2]}
      scrollWheelZoom
      className="h-full w-full"
      // Leaflet needs a non-transparent background under the tiles.
      style={{ background: "var(--muted)" }}
    >
      {/* Keyless OpenStreetMap base tiles. */}
      <TileLayer
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        maxZoom={19}
      />
      {/* The COG overlay, rendered on demand by TiTiler straight from B2.
          `key` forces a remount when the render config (URL) changes so tiles
          reload live. */}
      <TileLayer
        key={cogTileUrl}
        url={cogTileUrl}
        bounds={leafletBounds}
        minZoom={minzoom}
        maxZoom={maxzoom}
        opacity={0.85}
      />
      <FitToLayer bounds={leafletBounds} />
    </MapContainer>
  );
}
