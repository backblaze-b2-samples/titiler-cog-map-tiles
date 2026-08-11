"use client";

import { Layers, HardDrive, Grid2x2, Image } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingNotice } from "@/components/common/loading-notice";
import { useLayerStats } from "@/lib/queries";

/** Geospatial dashboard metrics, all derived from the COG layers in B2. */
export function StatsCards() {
  const { data: stats, isLoading, error, refetch } = useLayerStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards = [
    { title: "COG Layers", value: stats?.layer_count ?? 0, icon: Layers },
    { title: "Raster Bytes in B2", value: stats?.total_bytes_human ?? "0 B", icon: HardDrive },
    {
      title: "Total Megapixels",
      value: stats ? stats.total_megapixels.toFixed(1) : "0.0",
      icon: Grid2x2,
    },
    { title: "Tiles Served", value: stats?.tiles_served ?? 0, icon: Image },
  ];

  return (
    <>
      {isLoading && <LoadingNotice className="mb-3" subject="layer stats" />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card, i) => (
          <Card
            key={card.title}
            className={`card-hover animate-fade-in-up stagger-${i + 1}`}
          >
            <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
              <CardTitle className="text-xs font-semibold text-muted-foreground">
                {card.title}
              </CardTitle>
              <div className="stat-icon-wrap">
                <card.icon className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent className="pb-5 px-4">
              {isLoading ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <div className="stat-value">{card.value}</div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
