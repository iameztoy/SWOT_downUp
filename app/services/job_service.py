from __future__ import annotations

import uuid
from typing import Any

import yaml

from app.services.state import get_db, get_runner


def create_job(config: dict[str, Any]) -> dict[str, str]:
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    yaml_text = yaml.safe_dump(config, sort_keys=False)

    db = get_db()
    db.create_job(job_id=job_id, config_json=config, config_yaml=yaml_text, status="created")
    db.add_log(job_id, "INFO", "Job created")

    runner = get_runner()
    db.update_job(job_id, status="queued", message="Queued for execution", progress=0.01)
    runner.submit(job_id, config)

    return {"id": job_id, "status": "queued"}


def get_job(job_id: str) -> dict[str, Any] | None:
    return get_db().get_job(job_id)


def list_jobs() -> list[dict[str, Any]]:
    return get_db().list_jobs()


def get_job_logs(job_id: str) -> list[dict[str, Any]]:
    return get_db().get_logs(job_id)


def get_job_outputs(job_id: str) -> list[dict[str, Any]]:
    return get_db().get_outputs(job_id)


def save_aoi(aoi_id: str, name: str, method: str, geometry: dict[str, Any]) -> None:
    get_db().save_aoi(aoi_id=aoi_id, name=name, method=method, geometry_json=geometry)


def list_saved_aois() -> list[dict[str, Any]]:
    return get_db().list_aois()


def cancel_job(job_id: str) -> str | None:
    db = get_db()
    item = db.get_job(job_id)
    if not item:
        return None
    current_status = str(item.get("status", "created"))
    if current_status in {"completed", "failed", "canceled"}:
        return current_status
    db.update_job(job_id, status="canceled", message="Cancel requested by user")
    db.add_log(job_id, "WARNING", "Cancel requested")
    return "canceled"
