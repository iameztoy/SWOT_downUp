# Architecture Notes (Stabilized Vertical Slice)

This document locks the current module boundaries for the first end-to-end reference workflow.

## Core Principle

`swot_pipeline/` remains the reusable workflow core.
- CLI calls `swot_pipeline` directly.
- FastAPI job runner calls the same `swot_pipeline` modules.
- UI only orchestrates via API; it does not re-implement workflow logic.

## Module Boundaries

- `swot_pipeline/config.py`
  - shared YAML config model parsing/serialization for CLI + API + UI-generated snapshots.
- `swot_pipeline/products/`
  - product registry and per-product variable/QA metadata.
- `swot_pipeline/download/`
  - downloader registry and adapter interface.
  - uses `swot_pipeline/adapters/` as provider-specific transport implementations.
- `swot_pipeline/aoi/`
  - AOI parsing, validation, presets, and chunk planning helpers.
- `swot_pipeline/processing/`
  - local extraction, QA masking, and raster writing.
- `swot_pipeline/publish/`
  - optional GCS/EE publishing interfaces.
- `app/`
  - orchestration API, persisted jobs, logs, outputs, and background execution.
- `frontend/`
  - workflow wizard and job monitoring views.

## Stable Interfaces

- Product interface:
  - `ProductPlugin.build_quality_masks(extracted, quality_rules)`
  - `ProductPlugin.select_output_variables(explicit, optional)`
  - Registry: `swot_pipeline.products.list_product_plugins()`

- Downloader interface:
  - `search(date_start, date_end, aoi)`
  - `download(granules, output_dir)`
  - `validate_config()`
  - `get_capabilities()`
  - Registry: `swot_pipeline.download.get_downloader(config)`

- AOI interface:
  - `parse_aoi_payload(payload)`
  - `geometry_summary(geom)`
  - `chunk_geometry(...)`

- Workflow interface:
  - `search_granules(config)`
  - `download_granules(config, granules)`
  - `process_downloaded(config, granules)`
  - `publish_processed(config, processed)`
  - `run_job_from_config(config)`

- Job orchestration interface:
  - `POST /jobs` create + queue
  - `GET /jobs/{id}` status
  - `GET /jobs/{id}/logs`
  - `GET /jobs/{id}/outputs`
  - `POST /jobs/{id}/cancel`
  - status model: `created | validating | queued | running | completed | failed | canceled`

## Extension Points

- Add new product:
  - create plugin in `swot_pipeline/products/`
  - register in `swot_pipeline/products/registry.py`

- Add new downloader:
  - implement adapter in `swot_pipeline/download/`
  - register in `swot_pipeline/download/registry.py`

- Add new QA strategy:
  - extend product plugin QA methods and expose UI default in product metadata.

- Add new publish mode:
  - extend `swot_pipeline/publish/*` and keep `publish` section schema-compatible.

## Vertical Slice Status

- `earthaccess`: reference-ready end-to-end path.
- `podaac`: scaffolded adapter with config + capabilities + TODO notes.
- `harmony/swodlr`: scaffolded adapter with config + capabilities + TODO notes.
