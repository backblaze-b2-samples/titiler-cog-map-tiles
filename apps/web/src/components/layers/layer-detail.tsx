"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";
import type { RenderConfig } from "@titiler-cog-map-tiles/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useLayer } from "@/lib/queries";
import { tileUrl } from "@/lib/layer-render";
import { DeleteLayerDialog } from "./delete-layer-dialog";
import { EditLayerDialog } from "./edit-layer-dialog";
import { LayerMap } from "./layer-map";
import { RenderControls } from "./render-controls";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono tabular-nums">{value}</span>
    </div>
  );
}

export function LayerDetail({ id }: { id: string }) {
  const router = useRouter();
  const { data: layer, isLoading, error, refetch } = useLayer(id);
  // Ephemeral "run" render state — tunes the current view without persisting.
  // `override` starts null and is reset (during render, the React-sanctioned
  // pattern) whenever the layer's persisted render changes, e.g. after an edit.
  const [override, setOverride] = useState<RenderConfig | null>(null);
  const [seededKey, setSeededKey] = useState<string>("");
  const layerKey = layer ? `${layer.id}:${JSON.stringify(layer.render)}` : "";
  if (layer && layerKey !== seededKey) {
    setSeededKey(layerKey);
    setOverride(null);
  }

  if (isLoading || (!layer && !error)) {
    return <Skeleton className="h-[560px] w-full" />;
  }
  if (error || !layer) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const active = override ?? layer.render;
  const setRender = setOverride;
  const cogTileUrl = tileUrl(layer.tiles, active);
  const [w, s, e, n] = layer.bounds;
  const megapixels = (layer.width * layer.height) / 1_000_000;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0 space-y-1.5">
          <Button asChild variant="ghost" size="sm" className="-ml-2 h-7 text-muted-foreground">
            <Link href="/layers">
              <ArrowLeft className="h-3.5 w-3.5" />
              Layers
            </Link>
          </Button>
          <h1 className="page-title truncate">{layer.name}</h1>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{layer.band_count}-band</Badge>
            <Badge variant="secondary">{layer.dtype}</Badge>
            <Badge variant="secondary">
              zoom {layer.minzoom}–{layer.maxzoom}
            </Badge>
            <Badge variant="secondary">{layer.size_human}</Badge>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <EditLayerDialog
            layer={layer}
            trigger={
              <Button variant="outline" size="sm" className="h-8">
                <Pencil className="h-3.5 w-3.5" />
                Edit
              </Button>
            }
          />
          <DeleteLayerDialog
            layerId={layer.id}
            layerName={layer.name}
            onDeleted={() => router.push("/layers")}
            trigger={
              <Button variant="outline" size="sm" className="h-8 text-destructive">
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            }
          />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {/* The map + these live controls ARE the "run" verb: tiles are
              rendered on demand by TiTiler straight from B2. */}
          <LayerMap
            bounds={layer.bounds}
            center={layer.center}
            minzoom={layer.minzoom}
            maxzoom={layer.maxzoom}
            cogTileUrl={cogTileUrl}
          />
          <p className="mt-2 text-xs text-muted-foreground">
            Tiles are rendered live by TiTiler from the COG’s byte-ranges in B2 —
            no pre-rendered pyramid. Adjust the controls to re-tune the render.
          </p>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="border-b border-border px-5 py-4">
              <CardTitle className="card-title">Live render</CardTitle>
            </CardHeader>
            <CardContent className="p-5">
              <RenderControls
                render={active}
                onChange={setRender}
                colormaps={layer.colormaps}
                bandPresets={layer.band_presets}
                resamplings={layer.resamplings}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-border px-5 py-4">
              <CardTitle className="card-title">COG info</CardTitle>
            </CardHeader>
            <CardContent className="px-5 py-3">
              <Metric label="Bands" value={String(layer.band_count)} />
              <Metric label="Data type" value={layer.dtype} />
              <Metric label="Dimensions" value={`${layer.width} × ${layer.height}`} />
              <Metric label="Megapixels" value={megapixels.toFixed(1)} />
              <Metric label="Overviews" value={String(layer.overview_levels)} />
              <Metric label="Zoom range" value={`${layer.minzoom}–${layer.maxzoom}`} />
              <Metric
                label="Bounds W/S"
                value={`${w.toFixed(3)}, ${s.toFixed(3)}`}
              />
              <Metric
                label="Bounds E/N"
                value={`${e.toFixed(3)}, ${n.toFixed(3)}`}
              />
              <Metric label="Size in B2" value={layer.size_human} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
