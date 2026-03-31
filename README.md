# SWOT DownUp (Controlled Vertical Slice)

This repository now implements a **stabilized first vertical slice**:
- architecture preserved and documented,
- one fully usable end-to-end path using **earthaccess**,
- CLI + FastAPI + React UI using the same core workflow modules,
- non-reference downloaders kept as scaffolded extension points.

Initial target product: `SWOT_L2_HR_Raster_100m_D`.

## Completion Status

- `earthaccess` downloader: **reference-ready** for search + download + local processing.
- `podaac` downloader: **scaffolded** (adapter, config, capabilities, TODO).
- `harmony/swodlr` downloader: **scaffolded** (adapter, config, capabilities, TODO).
- Earth Engine publish path: preserved and optional.

## Architecture

- Architecture notes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Core pipeline remains in `swot_pipeline/` and is reused by both CLI and API job runner.
- Backend API + persistence live in `app/`.
- UI lives in `frontend/` and orchestrates via API only.

### Core Module Layout

```text
swot_pipeline/
  auth/ catalog/ download/ transform/ publish/ products/ qa/ storage/
  aoi/ config.py pipeline.py cli.py
app/
  api/ services/ models/ schemas/ tasks/
frontend/
  src/App.tsx + components
```

## Stable Interfaces

- Product plugin:
  - `build_quality_masks(extracted, quality_rules)`
  - `select_output_variables(explicit, optional)`
- Downloader adapter:
  - `search()`
  - `download()`
  - `validate_config()`
  - `get_capabilities()`
- AOI utilities:
  - `parse_aoi_payload()`
  - `geometry_summary()`
  - `chunk_geometry()`
- Workflow orchestration:
  - `search_granules()`
  - `download_granules()`
  - `process_downloaded()`
  - `run_job_from_config()`

## API Endpoints

- `GET /health`
- `GET /products`
- `GET /downloaders`
- `GET /aoi/presets`
- `POST /aoi/upload-shapefile`
- `POST /aoi/validate`
- `POST /config/preview`
- `POST /jobs`
- `POST /jobs/{id}/cancel`
- `GET /jobs`
- `GET /jobs/{id}`
- `GET /jobs/{id}/logs`
- `GET /jobs/{id}/outputs`
- `GET /aois`
- `POST /aois`

Job lifecycle states: `created`, `validating`, `queued`, `running`, `completed`, `failed`, `canceled`.

## Prerequisites (Smoke Test)

- Python 3.11+
- Optional Node 18+ for frontend
- Earthdata Login credentials
- Either `.netrc` entry for `urs.earthdata.nasa.gov` or env vars:
  - `EARTHDATA_USERNAME`
  - `EARTHDATA_PASSWORD`

Install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev,access,publish]
```

If you use `zsh` (including Codex app terminals), quote or escape extras to avoid glob expansion:

```bash
pip install -e '.[dev,access,publish]'
# or
pip install -e .\[dev,access,publish\]
```

## Backend Start

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Frontend Start

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Or from CLI:

```bash
swot-pipeline serve-ui
```

## CLI Smoke Test (earthaccess Reference Path)

Use [configs/smoke_earthaccess_small_aoi.yaml](configs/smoke_earthaccess_small_aoi.yaml):

```bash
swot-pipeline search configs/smoke_earthaccess_small_aoi.yaml --download-mode earthaccess
swot-pipeline download configs/smoke_earthaccess_small_aoi.yaml --download-mode earthaccess
swot-pipeline process configs/smoke_earthaccess_small_aoi.yaml
swot-pipeline run-job-from-config configs/smoke_earthaccess_small_aoi.yaml --download-mode earthaccess
```

## UI Smoke Test (earthaccess Reference Path)

1. Open UI.
2. Product: `SWOT_L2_HR_Raster_100m_D`.
3. Downloader: `earthaccess`.
4. AOI: choose small bbox or draw small rectangle.
5. Date range: short window.
6. Variables:
   - `wse`
   - `wse_qual`
   - `wse_uncert`
   - `water_frac`
   - `n_wse_pix`
7. QA preset: `qa_keep_basic`.
8. Run workflow from **Review & Run**.
9. Inspect **Jobs / Logs / Outputs**.

## Expected Successful Results

- Job status reaches `completed`.
- Source granules are downloaded under job chunk folders.
- Local processed raster outputs are created for selected variables.
- Config snapshot is written per job.
- Structured logs are available by job.
- Output catalog records include downloaded and processed artifacts.

## Common Failure Modes / Debugging

- Missing Earthdata credentials:
  - verify `.netrc` or `EARTHDATA_USERNAME`/`EARTHDATA_PASSWORD`.
- No granules found:
  - relax AOI or date range.
- AOI validation error:
  - verify geometry format (bbox/WKT/GeoJSON/shapefile zip).
- Raster/GDAL write issues:
  - disable COG temporarily (`write_cog: false`) and retest.
- Dependency issues:
  - ensure venv active and dependencies installed.

## Earth Engine for This Stage

- Publish modules and config hooks are preserved.
- Earth Engine upload is optional in this stage.
- Reference smoke path prioritizes local outputs.

## Tests

```bash
pytest
```

Current test coverage includes:
- config loading
- downloader registry
- product registry
- AOI parsing and chunking logic
- local variable extraction
- QA mask generation
- manifest generation
- API endpoint behavior
