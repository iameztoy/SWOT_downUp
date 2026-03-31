from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import typer

from swot_pipeline.config import load_config
from swot_pipeline.pipeline import (
    discover_local_granules,
    discover_processed_rasters,
    download_granules,
    process_downloaded,
    publish_processed,
    run_job_from_config,
    run_pipeline,
    search_granules,
)

app = typer.Typer(help="SWOT modular automation pipeline")


def _apply_download_mode(config, download_mode: str | None) -> None:
    if download_mode:
        config.data_access.mode = download_mode


@app.command("search")
def search_cmd(config_path: Path, download_mode: str | None = None, swodlr_cmd_template: str | None = None) -> None:
    config = load_config(config_path)
    _apply_download_mode(config, download_mode)
    granules = search_granules(config, swodlr_cmd_template=swodlr_cmd_template)
    typer.echo(f"Found {len(granules)} granules")
    for record in granules:
        typer.echo(
            json.dumps(
                {
                    "granule_id": record.granule_id,
                    "url": record.url,
                    "filename": record.filename,
                    "start_time": record.start_time.isoformat() if record.start_time else None,
                }
            )
        )


@app.command("download")
def download_cmd(config_path: Path, download_mode: str | None = None, swodlr_cmd_template: str | None = None) -> None:
    config = load_config(config_path)
    _apply_download_mode(config, download_mode)
    found = search_granules(config, swodlr_cmd_template=swodlr_cmd_template)
    downloaded = download_granules(config, found, swodlr_cmd_template=swodlr_cmd_template)
    typer.echo(f"Downloaded {len(downloaded)} files into {config.data_access.output_dir}")


@app.command("process")
def process_cmd(config_path: Path) -> None:
    config = load_config(config_path)
    granules = discover_local_granules(config.data_access.output_dir)
    if not granules:
        raise typer.BadParameter(f"No .nc files found in {config.data_access.output_dir}")

    outputs = process_downloaded(config, granules)
    typer.echo(f"Processed {len(outputs)} raster files into {config.process.output_dir}")


@app.command("publish")
def publish_cmd(config_path: Path) -> None:
    config = load_config(config_path)
    processed = discover_processed_rasters(config.process.output_dir)
    if not processed:
        raise typer.BadParameter(f"No .tif files found in {config.process.output_dir}")

    results = publish_processed(config, processed)
    typer.echo(f"Submitted {len(results)} Earth Engine publish tasks")
    for item in results:
        typer.echo(
            json.dumps(
                {
                    "asset_id": item.asset_id,
                    "task_id": item.task_id,
                    "state": item.state,
                }
            )
        )


@app.command("run-pipeline")
def run_pipeline_cmd(config_path: Path, download_mode: str | None = None, swodlr_cmd_template: str | None = None) -> None:
    config = load_config(config_path)
    _apply_download_mode(config, download_mode)
    found, downloaded, processed, published = run_pipeline(config, swodlr_cmd_template=swodlr_cmd_template)
    typer.echo(
        f"Pipeline complete: found={len(found)} downloaded={len(downloaded)} processed={len(processed)} "
        f"published={len(published)}"
    )


@app.command("run-job-from-config")
def run_job_from_config_cmd(
    config_path: Path,
    download_mode: str | None = None,
    swodlr_cmd_template: str | None = None,
) -> None:
    config = load_config(config_path)
    _apply_download_mode(config, download_mode)
    found, downloaded, processed, published = run_job_from_config(config, swodlr_cmd_template=swodlr_cmd_template)
    typer.echo(
        f"Job complete: found={len(found)} downloaded={len(downloaded)} processed={len(processed)} "
        f"published={len(published)}"
    )


@app.command("serve-ui")
def serve_ui_cmd(
    backend_host: str = "127.0.0.1",
    backend_port: int = 8000,
    run_frontend: bool = True,
    frontend_dir: Path = Path("frontend"),
) -> None:
    env = os.environ.copy()
    env.setdefault("VITE_API_BASE_URL", f"http://{backend_host}:{backend_port}")

    backend_cmd = [
        "python3",
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        backend_host,
        "--port",
        str(backend_port),
    ]

    if not run_frontend:
        subprocess.run(backend_cmd, check=True)
        return

    backend_proc = subprocess.Popen(backend_cmd, env=env)
    try:
        subprocess.run(["npm", "--prefix", str(frontend_dir), "run", "dev"], check=True, env=env)
    finally:
        backend_proc.terminate()
        backend_proc.wait(timeout=10)


if __name__ == "__main__":
    app()
