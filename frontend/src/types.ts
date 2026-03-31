export type ProductOption = {
  plugin: string
  short_name: string
  version?: string
  required_variables: string[]
  optional_variables: string[]
  supported_downloaders: string[]
  preferred_output_bands: string[]
}

export type DownloaderOption = {
  name: string
  display_name: string
  implementation_status?: 'reference_ready' | 'scaffolded'
  description?: string
  capabilities: {
    supports_search: boolean
    supports_direct_download: boolean
    supports_subscription: boolean
    supports_transformed_output: boolean
  }
}

export type AOIValidationResponse = {
  is_valid: boolean
  bbox: number[]
  area_km2: number
  size_class: string
  chunk_count: number
  chunks_preview: Array<{ label: string; bbox: number[]; area_km2: number }>
  warnings: string[]
  geometry_geojson: GeoJSON.GeoJsonObject
  crs: string
}

export type JobSummary = {
  id: string
  status: string
  created_at: string
  updated_at: string
  progress: number
  message?: string
  error?: string
  config: Record<string, unknown>
}

export type JobLog = {
  id: number
  job_id: string
  timestamp: string
  level: string
  message: string
  context: Record<string, unknown>
}

export type JobOutput = {
  id: number
  job_id: string
  output_type: string
  path: string
  metadata: Record<string, unknown>
  created_at: string
}
