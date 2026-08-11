"use client";

import { useState } from "react";
import { toast } from "sonner";
import type { LayerDetail, RenderConfig } from "@titiler-cog-map-tiles/shared";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUpdateLayer } from "@/lib/queries";
import { RenderControls } from "./render-controls";

/**
 * Edit a layer's name and default render config. The form opens PRE-FILLED from
 * the layer's sidecar (it edits a real resource, so no default hints), copying
 * the settings-form exemplar's shape.
 */
export function EditLayerDialog({
  layer,
  trigger,
}: {
  layer: LayerDetail;
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(layer.name);
  const [render, setRender] = useState<RenderConfig>(layer.render);
  const update = useUpdateLayer(layer.id);

  // Re-seed the form from the layer whenever the dialog is (re)opened.
  const onOpenChange = (next: boolean) => {
    if (next) {
      setName(layer.name);
      setRender(layer.render);
    }
    setOpen(next);
  };

  const onSave = () => {
    if (name.trim().length === 0) {
      toast.error("Name is required");
      return;
    }
    update.mutate(
      { name: name.trim(), render },
      {
        onSuccess: () => {
          toast.success("Layer updated");
          setOpen(false);
        },
        onError: (error) => toast.error("Update failed", { description: error.message }),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit layer</DialogTitle>
          <DialogDescription>
            Rename this layer and change its default render settings. Saved to the
            sidecar JSON in B2.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <div className="space-y-2">
            <Label htmlFor="layer-name">Name</Label>
            <Input
              id="layer-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <RenderControls
            render={render}
            onChange={setRender}
            colormaps={layer.colormaps}
            bandPresets={layer.band_presets}
            resamplings={layer.resamplings}
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={onSave} disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
