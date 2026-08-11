"use client";

import type { RenderConfig } from "@titiler-cog-map-tiles/shared";

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

const BAND_PRESET_LABELS: Record<string, string> = {
  single: "Single band + colormap",
  rgb: "RGB",
};

export interface RenderControlsProps {
  render: RenderConfig;
  onChange: (next: RenderConfig) => void;
  colormaps: string[];
  bandPresets: string[];
  resamplings: string[];
}

/**
 * Live render controls. Every change rebuilds the tile URL, so the map re-tunes
 * on the fly — these controls ARE the "run" verb. Finite-option fields are
 * selectors (never free text); only rescale min/max are numeric inputs.
 */
export function RenderControls({
  render,
  onChange,
  colormaps,
  bandPresets,
  resamplings,
}: RenderControlsProps) {
  const set = (patch: Partial<RenderConfig>) => onChange({ ...render, ...patch });
  const isSingle = render.band_preset === "single";

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Label>Band preset</Label>
        <RadioGroup
          value={render.band_preset}
          onValueChange={(value) =>
            set({ band_preset: value as RenderConfig["band_preset"] })
          }
          className="flex flex-wrap gap-4"
        >
          {bandPresets.map((preset) => (
            <label
              key={preset}
              className="flex cursor-pointer items-center gap-2 text-sm"
            >
              <RadioGroupItem value={preset} />
              {BAND_PRESET_LABELS[preset] ?? preset}
            </label>
          ))}
        </RadioGroup>
      </div>

      {isSingle && (
        <>
          <div className="space-y-2">
            <Label htmlFor="colormap">Colormap</Label>
            <Select value={render.colormap} onValueChange={(value) => set({ colormap: value })}>
              <SelectTrigger id="colormap" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {colormaps.map((cmap) => (
                  <SelectItem key={cmap} value={cmap} className="capitalize">
                    {cmap}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="rescale-min">Rescale min</Label>
              <Input
                id="rescale-min"
                type="number"
                className="font-mono tabular-nums"
                value={render.rescale_min ?? ""}
                onChange={(e) =>
                  set({ rescale_min: e.target.value === "" ? null : Number(e.target.value) })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="rescale-max">Rescale max</Label>
              <Input
                id="rescale-max"
                type="number"
                className="font-mono tabular-nums"
                value={render.rescale_max ?? ""}
                onChange={(e) =>
                  set({ rescale_max: e.target.value === "" ? null : Number(e.target.value) })
                }
              />
            </div>
          </div>
        </>
      )}

      <div className="space-y-2">
        <Label htmlFor="resampling">Resampling</Label>
        <Select
          value={render.resampling}
          onValueChange={(value) =>
            set({ resampling: value as RenderConfig["resampling"] })
          }
        >
          <SelectTrigger id="resampling" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {resamplings.map((mode) => (
              <SelectItem key={mode} value={mode} className="capitalize">
                {mode}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
