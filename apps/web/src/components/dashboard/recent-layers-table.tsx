"use client";

import Link from "next/link";
import { ArrowRight, Layers } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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

const MAX_ROWS = 6;

export function RecentLayersTable() {
  const { data: layers, isLoading, error, refetch } = useLayers();

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border px-5 py-4">
        <CardTitle className="card-title">Recent layers</CardTitle>
        <CardAction>
          <Button asChild variant="ghost" size="sm" className="h-7 text-xs">
            <Link href="/layers">
              View all
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="space-y-2 p-5">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : !layers || layers.length === 0 ? (
          <EmptyState
            icon={Layers}
            title="No layers yet"
            description="Create your first COG layer to see it here."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead className="hidden sm:table-cell">Bands</TableHead>
                <TableHead className="text-right">Size</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {layers.slice(0, MAX_ROWS).map((layer) => (
                <TableRow key={layer.id}>
                  <TableCell className="font-medium">
                    <Link href={`/layers/${layer.id}`} className="hover:underline">
                      {layer.name}
                    </Link>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell">
                    <Badge variant="secondary">{layer.band_count}</Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">
                    {layer.size_human}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
