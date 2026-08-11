import { CreateLayerForm } from "@/components/layers/create-layer-form";

export default function NewLayerPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">New layer</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Generate a synthetic sample COG, or upload a GeoTIFF to convert and
          store in Backblaze B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <CreateLayerForm />
      </div>
    </div>
  );
}
