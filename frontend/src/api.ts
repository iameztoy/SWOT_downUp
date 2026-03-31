import axios from 'axios'
import { AOIValidationResponse, DownloaderOption, JobLog, JobOutput, JobSummary, ProductOption } from './types'

const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://127.0.0.1:8000'

export const api = axios.create({
  baseURL: apiBase,
})

export async function fetchProducts(): Promise<ProductOption[]> {
  const { data } = await api.get<ProductOption[]>('/products')
  return data
}

export async function fetchDownloaders(): Promise<DownloaderOption[]> {
  const { data } = await api.get<DownloaderOption[]>('/downloaders')
  return data
}

export async function fetchAoiPresets(): Promise<Array<{ id: string; label: string; bbox: number[]; kind: string }>> {
  const { data } = await api.get('/aoi/presets')
  return data
}

export async function fetchSavedAois(): Promise<Array<{ id: string; name: string; method: string; geometry: GeoJSON.GeoJsonObject }>> {
  const { data } = await api.get('/aois')
  return data.aois
}

export async function uploadShapefileZip(file: File): Promise<{ zip_path: string }> {
  const body = new FormData()
  body.append('file', file)
  const { data } = await api.post('/aoi/upload-shapefile', body, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function validateAoi(payload: Record<string, unknown>): Promise<AOIValidationResponse> {
  const { data } = await api.post<AOIValidationResponse>('/aoi/validate', payload)
  return data
}

export async function previewConfig(config: Record<string, unknown>): Promise<{ normalized_config: Record<string, unknown>; yaml: string; warnings: string[] }> {
  const { data } = await api.post('/config/preview', { config })
  return data
}

export async function createJob(config: Record<string, unknown>): Promise<{ id: string; status: string }> {
  const { data } = await api.post('/jobs', { config })
  return data
}

export async function cancelJob(jobId: string): Promise<{ id: string; status: string }> {
  const { data } = await api.post(`/jobs/${jobId}/cancel`)
  return data
}

export async function listJobs(): Promise<JobSummary[]> {
  const { data } = await api.get('/jobs')
  return data.jobs
}

export async function getJob(jobId: string): Promise<JobSummary> {
  const { data } = await api.get(`/jobs/${jobId}`)
  return data
}

export async function getJobLogs(jobId: string): Promise<JobLog[]> {
  const { data } = await api.get(`/jobs/${jobId}/logs`)
  return data.logs
}

export async function getJobOutputs(jobId: string): Promise<JobOutput[]> {
  const { data } = await api.get(`/jobs/${jobId}/outputs`)
  return data.outputs
}
