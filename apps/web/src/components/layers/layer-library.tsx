"use client";

import Link from "next/link";
import { Layers, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useLayers } from "@/lib/queries";
import { DeleteLayerDialog } from "./delete-layer-dialog";

export function LayerLibrary() {
  const { data: layers, isLoading, error, refetch } = useLayers();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (!layers || layers.length === 0) {
    return (
      <EmptyState
        icon={Layers}
        title="No layers yet"
        description="Generate a synthetic sample COG or upload a GeoTIFF — it's stored in B2 and served as live map tiles."
        action={
          <Button asChild size="sm">
            <Link href="/layers/new">
              <Plus className="h-3.5 w-3.5" />
              New layer
            </Link>
          </Button>
        }
      />
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead className="hidden sm:table-cell">Bands</TableHead>
              <TableHead className="hidden md:table-cell">Type</TableHead>
              <TableHead className="hidden lg:table-cell">Zoom</TableHead>
              <TableHead className="text-right">Size</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {layers.map((layer) => (
              <TableRow key={layer.id} className="group">
                <TableCell className="font-medium">
                  <Link href={`/layers/${layer.id}`} className="hover:underline">
                    {layer.name}
                  </Link>
                </TableCell>
                <TableCell className="hidden sm:table-cell">
                  <Badge variant="secondary">{layer.band_count}</Badge>
                </TableCell>
                <TableCell className="hidden font-mono text-xs md:table-cell">
                  {layer.dtype}
                </TableCell>
                <TableCell className="hidden font-mono text-xs tabular-nums lg:table-cell">
                  {layer.minzoom}–{layer.maxzoom}
                </TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">
                  {layer.size_human}
                </TableCell>
                <TableCell className="text-right">
                  <DeleteLayerDialog
                    layerId={layer.id}
                    layerName={layer.name}
                    trigger={
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-muted-foreground hover:text-destructive"
                        aria-label={`Delete ${layer.name}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    }
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
