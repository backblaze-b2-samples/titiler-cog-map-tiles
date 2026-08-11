import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentLayersTable } from "@/components/dashboard/recent-layers-table";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5 max-w-prose">
            Cloud-Optimized GeoTIFF layers stored in Backblaze B2, served as
            dynamic map tiles read directly from object storage.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/layers/new">
            <Plus className="h-3.5 w-3.5" />
            New layer
          </Link>
        </Button>
      </div>
      <StatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <RecentLayersTable />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <Card className="h-full">
            <CardHeader className="border-b border-border px-5 py-4">
              <CardTitle className="card-title">How it works</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-5 text-sm text-muted-foreground">
              <p>
                Each layer is <strong>one COG object</strong> in your B2 bucket.
                There is no tile server holding a second copy of the data.
              </p>
              <p>
                When the map requests a tile, <strong>TiTiler</strong> uses GDAL
                to read only the byte-ranges it needs over the S3-compatible API
                and renders that tile on demand — so one growing archive is served
                directly, with zero duplication.
              </p>
              <p>
                <Link href="/layers/new" className="text-foreground underline">
                  Generate a sample layer
                </Link>{" "}
                to see it live on the map.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
