from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.api import (
    AOIValidateRequest,
    AOIValidateResponse,
    ConfigPreviewRequest,
    ConfigPreviewResponse,
    HealthResponse,
    JobCreateRequest,
    JobCreateResponse,
    JobDetailsResponse,
    JobLogsResponse,
    JobOutputsResponse,
    JobsListResponse,
    SaveAOIRequest,
    SaveAOIResponse,
    SavedAOIsResponse,
)
from app.services.aoi_service import get_presets, validate_aoi
from app.services.config_service import preview_config
from app.services.downloader_service import get_downloaders
from app.services.job_service import (
    cancel_job,
    create_job,
    get_job,
    get_job_logs,
    get_job_outputs,
    list_jobs,
    list_saved_aois,
    save_aoi,
)
from app.services.product_service import get_products
from swot_pipeline.models import ChunkingConfig

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="swot-pipeline-app")


@router.get("/products")
def products() -> list[dict[str, object]]:
    return get_products()


@router.get("/downloaders")
def downloaders() -> list[dict[str, object]]:
    return get_downloaders()


@router.get("/aoi/presets")
def aoi_presets() -> list[dict[str, object]]:
    return get_presets()


@router.post("/aoi/upload-shapefile")
async def aoi_upload_shapefile(file: UploadFile = File(...)) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only zipped shapefiles (.zip) are accepted")
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    output = upload_dir / f"{uuid.uuid4().hex}_{file.filename}"
    output.write_bytes(await file.read())
    return {"zip_path": str(output)}


@router.post("/aoi/validate", response_model=AOIValidateResponse)
def aoi_validate(request: AOIValidateRequest) -> AOIValidateResponse:
    payload = request.model_dump()
    chunking = ChunkingConfig(
        enabled=request.chunking_enabled,
        mode=request.chunking_mode,
        max_tile_area_km2=request.max_tile_area_km2,
        max_tile_span_deg=request.max_tile_span_deg,
        max_tiles=request.max_tiles,
    )
    summary = validate_aoi(payload, chunking=chunking)
    return AOIValidateResponse(**summary)


@router.post("/config/preview", response_model=ConfigPreviewResponse)
def config_preview(request: ConfigPreviewRequest) -> ConfigPreviewResponse:
    preview = preview_config(request.config)
    return ConfigPreviewResponse(**preview)


@router.post("/jobs", response_model=JobCreateResponse)
def jobs_create(request: JobCreateRequest) -> JobCreateResponse:
    created = create_job(request.config)
    return JobCreateResponse(**created)


@router.post("/jobs/{job_id}/cancel")
def jobs_cancel(job_id: str) -> dict[str, str]:
    status = cancel_job(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"id": job_id, "status": status}


@router.get("/jobs", response_model=JobsListResponse)
def jobs_list() -> JobsListResponse:
    jobs = [
        JobDetailsResponse(
            id=item["id"],
            status=item["status"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
            progress=float(item.get("progress", 0.0)),
            message=item.get("message"),
            error=item.get("error"),
            config=item.get("config", {}),
        )
        for item in list_jobs()
    ]
    return JobsListResponse(jobs=jobs)


@router.get("/jobs/{job_id}", response_model=JobDetailsResponse)
def jobs_get(job_id: str) -> JobDetailsResponse:
    item = get_job(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetailsResponse(
        id=item["id"],
        status=item["status"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
        progress=float(item.get("progress", 0.0)),
        message=item.get("message"),
        error=item.get("error"),
        config=item.get("config", {}),
    )


@router.get("/jobs/{job_id}/logs", response_model=JobLogsResponse)
def jobs_logs(job_id: str) -> JobLogsResponse:
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return JobLogsResponse(logs=get_job_logs(job_id))


@router.get("/jobs/{job_id}/outputs", response_model=JobOutputsResponse)
def jobs_outputs(job_id: str) -> JobOutputsResponse:
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOutputsResponse(outputs=get_job_outputs(job_id))


@router.post("/aois", response_model=SaveAOIResponse)
def aois_save(request: SaveAOIRequest) -> SaveAOIResponse:
    save_aoi(aoi_id=request.id, name=request.name, method=request.method, geometry=request.geometry)
    return SaveAOIResponse(id=request.id, name=request.name)


@router.get("/aois", response_model=SavedAOIsResponse)
def aois_list() -> SavedAOIsResponse:
    return SavedAOIsResponse(aois=list_saved_aois())
