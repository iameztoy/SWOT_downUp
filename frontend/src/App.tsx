import { ChangeEvent, useEffect, useMemo, useState } from 'react'
import YAML from 'yaml'

import JobsPanel from './components/JobsPanel'
import MapAoiSelector from './components/MapAoiSelector'
import {
  cancelJob,
  createJob,
  fetchAoiPresets,
  fetchDownloaders,
  fetchProducts,
  fetchSavedAois,
  getJobLogs,
  getJobOutputs,
  listJobs,
  previewConfig,
  uploadShapefileZip,
  validateAoi,
} from './api'
import { AOIValidationResponse, DownloaderOption, JobLog, JobOutput, JobSummary, ProductOption } from './types'

const STEPS = [
  'Workflow Setup',
  'AOI Selection',
  'Product & Variables',
  'Download Mode',
  'Processing & QA',
  'Publish to Earth Engine',
  'Review & Run',
  'Jobs / Logs / Outputs',
]

type DrawMode = 'none' | 'rectangle' | 'polygon'

type AoiMethod = 'bbox' | 'wkt' | 'geojson' | 'map_rectangle' | 'map_polygon' | 'preset' | 'shapefile_zip' | 'saved'

export default function App() {
  const [activeStep, setActiveStep] = useState(0)

  const [products, setProducts] = useState<ProductOption[]>([])
  const [downloaders, setDownloaders] = useState<DownloaderOption[]>([])
  const [presets, setPresets] = useState<Array<{ id: string; label: string; bbox: number[]; kind: string }>>([])
  const [savedAois, setSavedAois] = useState<Array<{ id: string; name: string; method: string; geometry: GeoJSON.GeoJsonObject }>>([])

  const [selectedProductPlugin, setSelectedProductPlugin] = useState('swot_l2_hr_raster_100m_d')
  const [selectedDownloader, setSelectedDownloader] = useState('earthaccess')
  const [dateStart, setDateStart] = useState('2024-06-01T00:00:00Z')
  const [dateEnd, setDateEnd] = useState('2024-06-03T00:00:00Z')

  const [aoiMethod, setAoiMethod] = useState<AoiMethod>('map_rectangle')
  const [drawMode, setDrawMode] = useState<DrawMode>('rectangle')
  const [mapGeometry, setMapGeometry] = useState<GeoJSON.GeoJsonObject | null>(null)
  const [uploadedGeojson, setUploadedGeojson] = useState<GeoJSON.GeoJsonObject | null>(null)
  const [manualWkt, setManualWkt] = useState('')
  const [bboxInput, setBboxInput] = useState({ minx: '-5', miny: '35', maxx: '5', maxy: '45' })
  const [selectedPresetId, setSelectedPresetId] = useState('world')
  const [selectedSavedAoiId, setSelectedSavedAoiId] = useState('')
  const [uploadedShapefileZipPath, setUploadedShapefileZipPath] = useState('')

  const [chunkingEnabled, setChunkingEnabled] = useState(true)
  const [chunkingMode, setChunkingMode] = useState<'auto' | 'always' | 'never'>('auto')
  const [maxTileArea, setMaxTileArea] = useState(300000)
  const [maxTileSpan, setMaxTileSpan] = useState(8)

  const [requiredVars, setRequiredVars] = useState<string[]>(['wse', 'wse_qual', 'wse_uncert', 'water_frac', 'n_wse_pix'])
  const [optionalVars, setOptionalVars] = useState<string[]>([])

  const [workflowStep, setWorkflowStep] = useState<'raw_only' | 'extract' | 'qa' | 'full'>('full')
  const [outputMode, setOutputMode] = useState<'ee_ready' | 'native_utm'>('ee_ready')
  const [writeCog, setWriteCog] = useState(true)
  const [includeQaMasks, setIncludeQaMasks] = useState(true)
  const [qaPreset, setQaPreset] = useState<'none' | 'qa_keep_basic' | 'qa_keep_strict'>('qa_keep_basic')

  const [publishEnabled, setPublishEnabled] = useState(false)
  const [publishImmediately, setPublishImmediately] = useState(true)
  const [publishMode, setPublishMode] = useState<'ingested' | 'external_image'>('ingested')
  const [gcsBucket, setGcsBucket] = useState('')
  const [gcsPrefix, setGcsPrefix] = useState('swot/ui')
  const [eeAssetRoot, setEeAssetRoot] = useState('users/your_user/swot_assets')
  const [gcpProjectId, setGcpProjectId] = useState('')

  const [earthdataUsername, setEarthdataUsername] = useState('')
  const [earthdataPassword, setEarthdataPassword] = useState('')
  const [netrcPath, setNetrcPath] = useState('')

  const [swodlrCmdTemplate, setSwodlrCmdTemplate] = useState('')
  const [usePodaacCli, setUsePodaacCli] = useState(false)

  const [aoiSummary, setAoiSummary] = useState<AOIValidationResponse | null>(null)
  const [previewYaml, setPreviewYaml] = useState('')
  const [previewWarnings, setPreviewWarnings] = useState<string[]>([])

  const [jobs, setJobs] = useState<JobSummary[]>([])
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [logs, setLogs] = useState<JobLog[]>([])
  const [outputs, setOutputs] = useState<JobOutput[]>([])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void (async () => {
      try {
        const [prod, dl, pr, sa] = await Promise.all([
          fetchProducts(),
          fetchDownloaders(),
          fetchAoiPresets(),
          fetchSavedAois(),
        ])
        setProducts(prod)
        setDownloaders(dl)
        setPresets(pr)
        setSavedAois(sa)
        if (prod.length > 0) {
          setSelectedProductPlugin(prod[0].plugin)
          setRequiredVars(prod[0].required_variables)
        }
      } catch (err) {
        setError(`Failed to load startup data: ${String(err)}`)
      }
    })()
  }, [])

  useEffect(() => {
    const id = window.setInterval(() => {
      void refreshJobs()
    }, 5000)
    void refreshJobs()
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    if (!selectedJobId) return
    const id = window.setInterval(() => {
      void refreshJobDetails(selectedJobId)
    }, 4000)
    void refreshJobDetails(selectedJobId)
    return () => window.clearInterval(id)
  }, [selectedJobId])

  const selectedProduct = useMemo(
    () => products.find((p) => p.plugin === selectedProductPlugin) ?? null,
    [products, selectedProductPlugin]
  )
  const selectedDownloaderInfo = useMemo(
    () => downloaders.find((d) => d.name === selectedDownloader) ?? null,
    [downloaders, selectedDownloader]
  )

  function toggleRequiredVar(name: string): void {
    setRequiredVars((prev) => (prev.includes(name) ? prev.filter((v) => v !== name) : [...prev, name]))
  }

  function toggleOptionalVar(name: string): void {
    setOptionalVars((prev) => (prev.includes(name) ? prev.filter((v) => v !== name) : [...prev, name]))
  }

  async function refreshJobs(): Promise<void> {
    try {
      const next = await listJobs()
      setJobs(next)
      if (!selectedJobId && next.length > 0) {
        setSelectedJobId(next[0].id)
      }
    } catch (err) {
      setError(`Failed to list jobs: ${String(err)}`)
    }
  }

  async function refreshJobDetails(jobId: string): Promise<void> {
    try {
      const [jobLogs, jobOutputs] = await Promise.all([getJobLogs(jobId), getJobOutputs(jobId)])
      setLogs(jobLogs)
      setOutputs(jobOutputs)
      await refreshJobs()
    } catch (err) {
      setError(`Failed to refresh job details: ${String(err)}`)
    }
  }

  function buildAoiPayload(): Record<string, unknown> {
    if (aoiMethod === 'bbox') {
      return {
        method: 'bbox',
        bbox: [
          Number(bboxInput.minx),
          Number(bboxInput.miny),
          Number(bboxInput.maxx),
          Number(bboxInput.maxy),
        ],
      }
    }

    if (aoiMethod === 'wkt') {
      return { method: 'wkt', wkt: manualWkt }
    }

    if (aoiMethod === 'preset') {
      return { method: 'preset', preset_id: selectedPresetId }
    }

    if (aoiMethod === 'saved') {
      const saved = savedAois.find((a) => a.id === selectedSavedAoiId)
      return { method: 'geojson', geojson: saved?.geometry }
    }

    if (aoiMethod === 'shapefile_zip') {
      return { method: 'shapefile_zip', zip_path: uploadedShapefileZipPath }
    }

    if (aoiMethod === 'geojson') {
      return { method: 'geojson', geojson: uploadedGeojson ?? mapGeometry }
    }

    if (aoiMethod === 'map_polygon') {
      return { method: 'map_polygon', geojson: mapGeometry }
    }

    return { method: 'map_rectangle', geojson: mapGeometry }
  }

  function buildConfig(): Record<string, unknown> {
    const aoiPayload = buildAoiPayload()
    const shortName = selectedProduct?.short_name ?? 'SWOT_L2_HR_Raster_100m_D'

    const cfg: Record<string, unknown> = {
      run_label: `ui-${new Date().toISOString()}`,
      date_range: {
        start: dateStart,
        end: dateEnd,
      },
      aoi: {
        method: aoiPayload.method,
        bbox: aoiPayload.bbox,
        polygon_wkt: aoiPayload.wkt,
        geojson: aoiPayload.geojson,
        preset_id: aoiPayload.preset_id,
        polygon_path: aoiPayload.zip_path,
      },
      data_access: {
        mode: selectedDownloader,
        short_name: shortName,
        version: selectedProduct?.version ?? '2.0',
        provider: 'POCLOUD',
        output_dir: 'data/raw',
        page_size: 200,
        max_results: 2000,
        downloader_options: {
          swodlr_cmd_template: swodlrCmdTemplate || undefined,
          use_downloader_cli: usePodaacCli,
        },
      },
      process: {
        output_dir: 'data/processed',
        output_mode: outputMode,
        workflow_step: workflowStep,
        write_cog: writeCog,
        include_qa_masks: includeQaMasks,
        nodata: -9999,
        variables: [...requiredVars, ...optionalVars],
        optional_variables: [],
        quality_rules: {
          basic_max_wse_qual: 1,
          strict_max_wse_qual: 0,
          apply_mask: qaPreset === 'none' ? null : qaPreset,
        },
      },
      publish: {
        enabled: publishEnabled,
        publish_immediately: publishImmediately,
        ee_mode: publishMode,
        gcs_bucket: gcsBucket || null,
        gcs_prefix: gcsPrefix,
        ee_asset_root: eeAssetRoot || null,
        project_id: gcpProjectId || null,
      },
      auth: {
        earthdata_username: earthdataUsername || null,
        earthdata_password: earthdataPassword || null,
        netrc_path: netrcPath || null,
      },
      product: {
        plugin: selectedProductPlugin,
        short_name: shortName,
        version: selectedProduct?.version ?? '2.0',
        preferred_output_bands: selectedProduct?.preferred_output_bands ?? requiredVars,
      },
      chunking: {
        enabled: chunkingEnabled,
        mode: chunkingMode,
        max_tile_area_km2: maxTileArea,
        max_tile_span_deg: maxTileSpan,
        max_tiles: 400,
      },
    }

    return cfg
  }

  async function onValidateAoi(): Promise<void> {
    setLoading(true)
    setError(null)
    try {
      const payload = {
        ...buildAoiPayload(),
        chunking_enabled: chunkingEnabled,
        chunking_mode: chunkingMode,
        max_tile_area_km2: maxTileArea,
        max_tile_span_deg: maxTileSpan,
      }
      const response = await validateAoi(payload)
      setAoiSummary(response)
    } catch (err) {
      setError(`AOI validation failed: ${String(err)}`)
    } finally {
      setLoading(false)
    }
  }

  async function onPreviewConfig(): Promise<void> {
    setLoading(true)
    setError(null)
    try {
      const preview = await previewConfig(buildConfig())
      setPreviewYaml(preview.yaml)
      setPreviewWarnings(preview.warnings)
      setActiveStep(6)
    } catch (err) {
      setError(`Config preview failed: ${String(err)}`)
    } finally {
      setLoading(false)
    }
  }

  async function onRunJob(): Promise<void> {
    setLoading(true)
    setError(null)
    try {
      const created = await createJob(buildConfig())
      setSelectedJobId(created.id)
      setActiveStep(7)
      await refreshJobs()
    } catch (err) {
      setError(`Job start failed: ${String(err)}`)
    } finally {
      setLoading(false)
    }
  }

  async function onCancelJob(jobId: string): Promise<void> {
    setLoading(true)
    setError(null)
    try {
      await cancelJob(jobId)
      await refreshJobDetails(jobId)
    } catch (err) {
      setError(`Cancel failed: ${String(err)}`)
    } finally {
      setLoading(false)
    }
  }

  async function onUploadGeojson(file: File): Promise<void> {
    const text = await file.text()
    const parsed = JSON.parse(text) as GeoJSON.GeoJsonObject
    setUploadedGeojson(parsed)
    setMapGeometry(parsed)
  }

  async function onUploadShapefile(file: File): Promise<void> {
    const result = await uploadShapefileZip(file)
    setUploadedShapefileZipPath(result.zip_path)
  }

  async function onImportConfig(file: File): Promise<void> {
    const text = await file.text()
    const parsed = YAML.parse(text) as Record<string, any>

    if (parsed.product?.plugin) setSelectedProductPlugin(parsed.product.plugin)
    if (parsed.data_access?.mode) setSelectedDownloader(parsed.data_access.mode)
    if (parsed.date_range?.start) setDateStart(parsed.date_range.start)
    if (parsed.date_range?.end) setDateEnd(parsed.date_range.end)
    if (parsed.aoi?.method) setAoiMethod(parsed.aoi.method)
    if (parsed.aoi?.bbox?.length === 4) {
      setBboxInput({
        minx: String(parsed.aoi.bbox[0]),
        miny: String(parsed.aoi.bbox[1]),
        maxx: String(parsed.aoi.bbox[2]),
        maxy: String(parsed.aoi.bbox[3]),
      })
    }
    if (parsed.aoi?.geojson) {
      setUploadedGeojson(parsed.aoi.geojson)
      setMapGeometry(parsed.aoi.geojson)
    }
    if (parsed.process?.variables) {
      setRequiredVars(parsed.process.variables)
      setOptionalVars([])
    }
    if (parsed.chunking?.mode) setChunkingMode(parsed.chunking.mode)
    if (parsed.chunking?.enabled !== undefined) setChunkingEnabled(Boolean(parsed.chunking.enabled))
    if (parsed.process?.workflow_step) setWorkflowStep(parsed.process.workflow_step)
    if (parsed.process?.output_mode) setOutputMode(parsed.process.output_mode)
    if (parsed.publish?.enabled !== undefined) setPublishEnabled(Boolean(parsed.publish.enabled))
  }

  function onDownloadConfigYaml(): void {
    if (!previewYaml) return
    const blob = new Blob([previewYaml], { type: 'text/yaml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `swot_pipeline_${Date.now()}.yaml`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <h1>SWOT Pipeline Studio</h1>
        <p>Configurable CLI + UI workflow orchestration for local and continental-scale SWOT processing.</p>
      </header>

      <nav className="step-nav">
        {STEPS.map((step, idx) => (
          <button
            key={step}
            type="button"
            className={`step-pill ${activeStep === idx ? 'active' : ''}`}
            onClick={() => setActiveStep(idx)}
          >
            {idx + 1}. {step}
          </button>
        ))}
      </nav>

      {error && <div className="alert error">{error}</div>}

      <main className="content-grid">
        {activeStep === 0 && (
          <section className="card">
            <h2>Workflow Setup</h2>
            <div className="grid-2">
              <label>
                Product
                <select value={selectedProductPlugin} onChange={(e) => setSelectedProductPlugin(e.target.value)}>
                  {products.map((p) => (
                    <option key={p.plugin} value={p.plugin}>
                      {p.short_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Downloader Mode
                <select value={selectedDownloader} onChange={(e) => setSelectedDownloader(e.target.value)}>
                  {downloaders.map((d) => (
                    <option key={d.name} value={d.name}>
                      {d.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Date Start (UTC)
                <input value={dateStart} onChange={(e) => setDateStart(e.target.value)} />
              </label>
              <label>
                Date End (UTC)
                <input value={dateEnd} onChange={(e) => setDateEnd(e.target.value)} />
              </label>
            </div>

            <div className="inline-row">
              <label>
                Import Existing YAML Config
                <input
                  type="file"
                  accept=".yaml,.yml"
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    void onImportConfig(file)
                  }}
                />
              </label>
            </div>
          </section>
        )}

        {activeStep === 1 && (
          <section className="card">
            <h2>AOI Selection</h2>
            <div className="grid-2">
              <label>
                AOI Method
                <select
                  value={aoiMethod}
                  onChange={(e) => {
                    const method = e.target.value as AoiMethod
                    setAoiMethod(method)
                    if (method === 'map_rectangle') setDrawMode('rectangle')
                    if (method === 'map_polygon') setDrawMode('polygon')
                    if (!method.startsWith('map_')) setDrawMode('none')
                  }}
                >
                  <option value="map_rectangle">Draw rectangle on map</option>
                  <option value="map_polygon">Draw polygon on map</option>
                  <option value="geojson">Upload/Paste GeoJSON</option>
                  <option value="shapefile_zip">Upload zipped shapefile</option>
                  <option value="wkt">Paste WKT</option>
                  <option value="bbox">Manual bounding box</option>
                  <option value="preset">Predefined region</option>
                  <option value="saved">Saved AOI</option>
                </select>
              </label>

              <label>
                Chunking Mode
                <select value={chunkingMode} onChange={(e) => setChunkingMode(e.target.value as 'auto' | 'always' | 'never')}>
                  <option value="auto">Auto</option>
                  <option value="always">Always chunk</option>
                  <option value="never">Never chunk</option>
                </select>
              </label>
              <label className="checkbox-row">
                <input type="checkbox" checked={chunkingEnabled} onChange={(e) => setChunkingEnabled(e.target.checked)} />
                Enable chunking
              </label>
            </div>

            {(aoiMethod === 'map_rectangle' || aoiMethod === 'map_polygon' || aoiMethod === 'geojson') && (
              <MapAoiSelector geometry={mapGeometry} drawMode={drawMode} onGeometryChange={setMapGeometry} />
            )}

            {aoiMethod === 'geojson' && (
              <label>
                Upload GeoJSON
                <input
                  type="file"
                  accept=".json,.geojson"
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    void onUploadGeojson(file)
                  }}
                />
              </label>
            )}

            {aoiMethod === 'shapefile_zip' && (
              <label>
                Upload zipped shapefile (.zip)
                <input
                  type="file"
                  accept=".zip"
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    void onUploadShapefile(file)
                  }}
                />
                <small>{uploadedShapefileZipPath || 'No file uploaded yet.'}</small>
              </label>
            )}

            {aoiMethod === 'wkt' && (
              <label>
                WKT Geometry
                <textarea value={manualWkt} onChange={(e) => setManualWkt(e.target.value)} rows={5} />
              </label>
            )}

            {aoiMethod === 'bbox' && (
              <div className="grid-4">
                <label>
                  minx
                  <input value={bboxInput.minx} onChange={(e) => setBboxInput({ ...bboxInput, minx: e.target.value })} />
                </label>
                <label>
                  miny
                  <input value={bboxInput.miny} onChange={(e) => setBboxInput({ ...bboxInput, miny: e.target.value })} />
                </label>
                <label>
                  maxx
                  <input value={bboxInput.maxx} onChange={(e) => setBboxInput({ ...bboxInput, maxx: e.target.value })} />
                </label>
                <label>
                  maxy
                  <input value={bboxInput.maxy} onChange={(e) => setBboxInput({ ...bboxInput, maxy: e.target.value })} />
                </label>
              </div>
            )}

            {aoiMethod === 'preset' && (
              <label>
                Region Preset
                <select value={selectedPresetId} onChange={(e) => setSelectedPresetId(e.target.value)}>
                  {presets.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.label} ({preset.kind})
                    </option>
                  ))}
                </select>
              </label>
            )}

            {aoiMethod === 'saved' && (
              <label>
                Saved AOI
                <select value={selectedSavedAoiId} onChange={(e) => setSelectedSavedAoiId(e.target.value)}>
                  <option value="">Select saved AOI</option>
                  {savedAois.map((saved) => (
                    <option key={saved.id} value={saved.id}>
                      {saved.name}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <div className="inline-row">
              <label>
                Max tile area km²
                <input type="number" value={maxTileArea} onChange={(e) => setMaxTileArea(Number(e.target.value))} />
              </label>
              <label>
                Max tile span degrees
                <input type="number" value={maxTileSpan} onChange={(e) => setMaxTileSpan(Number(e.target.value))} />
              </label>
              <button type="button" onClick={() => void onValidateAoi()} disabled={loading}>
                Validate AOI
              </button>
            </div>

            {aoiSummary && (
              <div className="summary-box">
                <strong>AOI Summary</strong>
                <p>Area: {aoiSummary.area_km2.toFixed(2)} km²</p>
                <p>BBox: [{aoiSummary.bbox.map((v) => v.toFixed(4)).join(', ')}]</p>
                <p>CRS: {aoiSummary.crs}</p>
                <p>Scale class: {aoiSummary.size_class}</p>
                <p>Estimated chunks: {aoiSummary.chunk_count}</p>
                {aoiSummary.warnings.length > 0 && (
                  <ul>
                    {aoiSummary.warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </section>
        )}

        {activeStep === 2 && (
          <section className="card">
            <h2>Product & Variables</h2>
            <p>Required and optional bands are plugin-driven for extensibility.</p>
            <div className="variable-grid">
              {selectedProduct?.required_variables.map((v) => (
                <label key={v} className="checkbox-row">
                  <input type="checkbox" checked={requiredVars.includes(v)} onChange={() => toggleRequiredVar(v)} />
                  {v}
                </label>
              ))}
              {selectedProduct?.optional_variables.map((v) => (
                <label key={v} className="checkbox-row optional">
                  <input type="checkbox" checked={optionalVars.includes(v)} onChange={() => toggleOptionalVar(v)} />
                  {v}
                </label>
              ))}
            </div>
          </section>
        )}

        {activeStep === 3 && (
          <section className="card">
            <h2>Download Mode</h2>
            {selectedDownloaderInfo?.implementation_status === 'scaffolded' && (
              <div className="alert warning">
                {selectedDownloaderInfo.display_name} is currently scaffolded. Use <strong>earthaccess</strong> for the
                fully supported smoke-test path in this stage.
              </div>
            )}
            <div className="grid-2">
              <label>
                Mode
                <select value={selectedDownloader} onChange={(e) => setSelectedDownloader(e.target.value)}>
                  {downloaders.map((d) => (
                    <option key={d.name} value={d.name}>
                      {d.display_name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Earthdata username (optional)
                <input value={earthdataUsername} onChange={(e) => setEarthdataUsername(e.target.value)} />
              </label>

              <label>
                Earthdata password (optional)
                <input type="password" value={earthdataPassword} onChange={(e) => setEarthdataPassword(e.target.value)} />
              </label>

              <label>
                netrc path (optional)
                <input value={netrcPath} onChange={(e) => setNetrcPath(e.target.value)} />
              </label>
            </div>

            {selectedDownloader === 'podaac' && (
              <label className="checkbox-row">
                <input type="checkbox" checked={usePodaacCli} onChange={(e) => setUsePodaacCli(e.target.checked)} />
                Use PO.DAAC downloader CLI integration
              </label>
            )}

            {selectedDownloader === 'harmony' && (
              <label>
                SWODLR/Harmony command template
                <input
                  value={swodlrCmdTemplate}
                  onChange={(e) => setSwodlrCmdTemplate(e.target.value)}
                  placeholder='example: swodlr --input {input_url} --output {output_path}'
                />
              </label>
            )}
          </section>
        )}

        {activeStep === 4 && (
          <section className="card">
            <h2>Processing & QA</h2>
            <div className="grid-2">
              <label>
                Workflow depth
                <select value={workflowStep} onChange={(e) => setWorkflowStep(e.target.value as 'raw_only' | 'extract' | 'qa' | 'full')}>
                  <option value="raw_only">Raw download only</option>
                  <option value="extract">Download + extraction</option>
                  <option value="qa">Download + extraction + QA</option>
                  <option value="full">Full pipeline</option>
                </select>
              </label>
              <label>
                Output projection
                <select value={outputMode} onChange={(e) => setOutputMode(e.target.value as 'ee_ready' | 'native_utm')}>
                  <option value="ee_ready">EE-ready lat/lon</option>
                  <option value="native_utm">Preserve native UTM</option>
                </select>
              </label>
              <label className="checkbox-row">
                <input type="checkbox" checked={writeCog} onChange={(e) => setWriteCog(e.target.checked)} />
                Write COG
              </label>
              <label className="checkbox-row">
                <input type="checkbox" checked={includeQaMasks} onChange={(e) => setIncludeQaMasks(e.target.checked)} />
                Include QA mask bands
              </label>
              <label>
                QA apply mask preset
                <select value={qaPreset} onChange={(e) => setQaPreset(e.target.value as 'none' | 'qa_keep_basic' | 'qa_keep_strict')}>
                  <option value="none">Do not mask output</option>
                  <option value="qa_keep_basic">qa_keep_basic</option>
                  <option value="qa_keep_strict">qa_keep_strict</option>
                </select>
              </label>
            </div>
          </section>
        )}

        {activeStep === 5 && (
          <section className="card">
            <h2>Publish to Earth Engine</h2>
            <div className="grid-2">
              <label className="checkbox-row">
                <input type="checkbox" checked={publishEnabled} onChange={(e) => setPublishEnabled(e.target.checked)} />
                Enable publish stage
              </label>
              <label className="checkbox-row">
                <input type="checkbox" checked={publishImmediately} onChange={(e) => setPublishImmediately(e.target.checked)} />
                Publish immediately after local processing
              </label>
              <label>
                Publish mode
                <select value={publishMode} onChange={(e) => setPublishMode(e.target.value as 'ingested' | 'external_image')}>
                  <option value="ingested">Ingested image asset</option>
                  <option value="external_image">External COG-backed image asset</option>
                </select>
              </label>
              <label>
                GCP Project ID
                <input value={gcpProjectId} onChange={(e) => setGcpProjectId(e.target.value)} />
              </label>
              <label>
                GCS Bucket
                <input value={gcsBucket} onChange={(e) => setGcsBucket(e.target.value)} />
              </label>
              <label>
                GCS Prefix
                <input value={gcsPrefix} onChange={(e) => setGcsPrefix(e.target.value)} />
              </label>
              <label>
                EE Asset Root
                <input value={eeAssetRoot} onChange={(e) => setEeAssetRoot(e.target.value)} />
              </label>
            </div>
          </section>
        )}

        {activeStep === 6 && (
          <section className="card">
            <h2>Review & Run</h2>
            <div className="inline-row">
              <button type="button" onClick={() => void onPreviewConfig()} disabled={loading}>
                Generate Config Preview
              </button>
              <button type="button" onClick={() => void onRunJob()} disabled={loading}>
                Launch Workflow Job
              </button>
              <button type="button" onClick={onDownloadConfigYaml} disabled={!previewYaml}>
                Download YAML Snapshot
              </button>
            </div>
            {previewWarnings.length > 0 && (
              <div className="alert warning">
                {previewWarnings.map((w) => (
                  <p key={w}>{w}</p>
                ))}
              </div>
            )}
            <textarea className="yaml-preview" value={previewYaml} readOnly rows={22} />
          </section>
        )}

        {activeStep === 7 && (
          <section className="card">
            <h2>Jobs / Logs / Outputs</h2>
            <JobsPanel
              jobs={jobs}
              selectedJobId={selectedJobId}
              onSelectJob={setSelectedJobId}
              onCancelJob={(jobId) => void onCancelJob(jobId)}
              logs={logs}
              outputs={outputs}
            />
          </section>
        )}
      </main>
    </div>
  )
}
