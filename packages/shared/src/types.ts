export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- COG map Layers (this sample's primary entity) ---

export type BandPreset = "single" | "rgb";
export type Resampling = "nearest" | "bilinear" | "cubic";
export type SampleKind = "elevation" | "rgb";

/** How a layer is painted into tiles. Re-tunable live in the map viewer. */
export interface RenderConfig {
  band_preset: BandPreset;
  colormap: string;
  rescale_min: number | null;
  rescale_max: number | null;
  resampling: Resampling;
  bidx: number;
}

export interface LayerSummary {
  id: string;
  name: string;
  size_bytes: number;
  size_human: string;
  band_count: number;
  dtype: string;
  minzoom: number;
  maxzoom: number;
  bounds: number[]; // [w, s, e, n] WGS84
  uploaded_at: string;
}

export interface LayerDetail extends LayerSummary {
  center: number[]; // [lng, lat, zoom]
  width: number;
  height: number;
  overview_levels: number;
  colorinterp: string[];
  render: RenderConfig;
  /** App-relative tile template; prepend API_BASE and append render params. */
  tiles: string;
  colormaps: string[];
  band_presets: string[];
  resamplings: string[];
}

export interface LayerStats {
  layer_count: number;
  total_bytes: number;
  total_bytes_human: string;
  total_megapixels: number;
  tiles_served: number;
}

export interface GenerateLayerRequest {
  name: string;
  kind: SampleKind;
  /** Optional initial render overrides; omit to let the server auto-pick. */
  colormap?: string | null;
  band_preset?: BandPreset | null;
}

export interface UpdateLayerRequest {
  name: string;
  render: RenderConfig;
}
