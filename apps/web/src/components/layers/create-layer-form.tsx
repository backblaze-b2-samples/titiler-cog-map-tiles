"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, Sparkles } from "lucide-react";
import { toast } from "sonner";
import type { BandPreset, SampleKind } from "@titiler-cog-map-tiles/shared";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateLayer, useGenerateLayer } from "@/lib/queries";

// Finite option sets (mirror the backend COLORMAPS / RESAMPLINGS). Selectors,
// never free text.
const COLORMAPS = ["viridis", "terrain", "greys", "rdylgn", "magma", "plasma", "spectral"];
const RESAMPLINGS = ["nearest", "bilinear", "cubic"];

type Source = "upload" | "generate";

function Hint({ children }: { children: React.ReactNode }) {
  return <p className="text-xs text-muted-foreground">{children}</p>;
}

export function CreateLayerForm() {
  const router = useRouter();
  const create = useCreateLayer();
  const generate = useGenerateLayer();

  const [source, setSource] = useState<Source>("generate");
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState<SampleKind>("elevation");
  const [resampling, setResampling] = useState("nearest");
  // "auto" = let the server pick from the raster (safe default, never autofilled).
  const [colormap, setColormap] = useState("auto");
  const [bandPreset, setBandPreset] = useState("auto");

  const pending = create.isPending || generate.isPending;
  const colormapOverride = colormap === "auto" ? undefined : colormap;
  const bandPresetOverride =
    bandPreset === "auto" ? undefined : (bandPreset as BandPreset);

  const goToLayer = (id: string) => {
    toast.success("Layer created", { description: "Stored in B2 as a COG." });
    router.push(`/layers/${id}`);
  };
  const onError = (label: string) => (error: { message: string }) =>
    toast.error(label, { description: error.message });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim().length === 0) {
      toast.error("Name is required");
      return;
    }
    if (source === "upload") {
      if (!file) {
        toast.error("Choose a GeoTIFF to ingest");
        return;
      }
      create.mutate(
        {
          file,
          name: name.trim(),
          resampling,
          colormap: colormapOverride,
          bandPreset: bandPresetOverride,
        },
        { onSuccess: (layer) => goToLayer(layer.id), onError: onError("Ingest failed") }
      );
    } else {
      generate.mutate(
        {
          name: name.trim(),
          kind,
          colormap: colormapOverride,
          band_preset: bandPresetOverride,
        },
        { onSuccess: (layer) => goToLayer(layer.id), onError: onError("Generate failed") }
      );
    }
  };

  return (
    <form onSubmit={onSubmit} className="max-w-2xl space-y-6">
      <Card>
        <CardHeader className="border-b border-border px-5 py-4">
          <CardTitle className="card-title">Source</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 p-5">
          <RadioGroup
            value={source}
            onValueChange={(value) => setSource(value as Source)}
            className="grid gap-3 sm:grid-cols-2"
          >
            <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3 text-sm">
              <RadioGroupItem value="generate" className="mt-0.5" />
              <span>
                <span className="flex items-center gap-1.5 font-medium">
                  <Sparkles className="h-3.5 w-3.5" /> Generate sample layer
                </span>
                <Hint>Synthetic, georeferenced COG — no data or key needed.</Hint>
              </span>
            </label>
            <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3 text-sm">
              <RadioGroupItem value="upload" className="mt-0.5" />
              <span>
                <span className="flex items-center gap-1.5 font-medium">
                  <FileUp className="h-3.5 w-3.5" /> Upload GeoTIFF
                </span>
                <Hint>Converted to a COG server-side, then stored in B2.</Hint>
              </span>
            </label>
          </RadioGroup>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-border px-5 py-4">
          <CardTitle className="card-title">Layer</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5 p-5">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. sf-elevation"
            />
            <Hint>A short label for the layer library.</Hint>
          </div>

          {source === "generate" ? (
            <div className="space-y-2">
              <Label htmlFor="kind">Sample kind</Label>
              <Select value={kind} onValueChange={(value) => setKind(value as SampleKind)}>
                <SelectTrigger id="kind" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="elevation">Elevation (single band)</SelectItem>
                  <SelectItem value="rgb">RGB (3 band)</SelectItem>
                </SelectContent>
              </Select>
              <Hint>Both overlay San Francisco so they line up on the map.</Hint>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="file">GeoTIFF</Label>
                <Input
                  id="file"
                  type="file"
                  accept=".tif,.tiff,image/tiff"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                <Hint>Must be georeferenced (have a CRS). Converted to a valid COG.</Hint>
              </div>
              <div className="space-y-2">
                <Label htmlFor="resampling">Overview resampling</Label>
                <Select value={resampling} onValueChange={setResampling}>
                  <SelectTrigger id="resampling" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {RESAMPLINGS.map((mode) => (
                      <SelectItem key={mode} value={mode} className="capitalize">
                        {mode}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Hint>Used when building the COG’s internal overviews.</Hint>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-border px-5 py-4">
          <CardTitle className="card-title">Render defaults (optional)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5 p-5">
          <div className="space-y-2">
            <Label>Band preset</Label>
            <RadioGroup
              value={bandPreset}
              onValueChange={setBandPreset}
              className="flex flex-wrap gap-4"
            >
              {[
                ["auto", "Auto (from raster)"],
                ["single", "Single band + colormap"],
                ["rgb", "RGB"],
              ].map(([value, label]) => (
                <label key={value} className="flex cursor-pointer items-center gap-2 text-sm">
                  <RadioGroupItem value={value} />
                  {label}
                </label>
              ))}
            </RadioGroup>
            <Hint>Default: Single band + colormap for single-band rasters, RGB for 3-band.</Hint>
          </div>
          <div className="space-y-2">
            <Label htmlFor="colormap">Colormap</Label>
            <Select value={colormap} onValueChange={setColormap}>
              <SelectTrigger id="colormap" className="w-full sm:w-72">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Auto (terrain)</SelectItem>
                {COLORMAPS.map((cmap) => (
                  <SelectItem key={cmap} value={cmap} className="capitalize">
                    {cmap}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Hint>terrain works well for elevation. Leave blank fields to auto-scale.</Hint>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => router.push("/layers")}>
          Cancel
        </Button>
        <Button type="submit" disabled={pending}>
          {pending
            ? "Working…"
            : source === "generate"
              ? "Generate layer"
              : "Ingest GeoTIFF"}
        </Button>
      </div>
    </form>
  );
}
