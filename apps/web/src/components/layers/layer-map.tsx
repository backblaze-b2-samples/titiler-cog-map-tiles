"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";
import type { LeafletMapProps } from "./leaflet-map";

// Load Leaflet only on the client: it references `window` at module scope, so
// server-rendering it throws. A skeleton fills the frame while it loads.
const LeafletMap = dynamic(
  () => import("./leaflet-map").then((mod) => mod.LeafletMap),
  {
    ssr: false,
    loading: () => <Skeleton className="h-full w-full" />,
  }
);

export function LayerMap(props: LeafletMapProps) {
  return (
    <div className="h-[480px] w-full overflow-hidden rounded-lg border border-border">
      <LeafletMap {...props} />
    </div>
  );
}
