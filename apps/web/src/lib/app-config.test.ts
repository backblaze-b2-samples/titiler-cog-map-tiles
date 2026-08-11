import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("TiTiler COG Map Tiles");
    expect(APP_DESCRIPTION).toBe(
      "Serve dynamic XYZ map tiles from Cloud-Optimized GeoTIFFs stored in Backblaze B2"
    );
  });
});
