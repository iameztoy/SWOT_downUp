from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from swot_pipeline.models import AuthConfig, PublishConfig, PublishResult
from swot_pipeline.utils.auth import initialize_earth_engine


class EarthEnginePublisher:
    def __init__(self, auth: AuthConfig, publish: PublishConfig):
        self.auth = auth
        self.publish = publish

    def submit_manifest(self, manifest: dict[str, Any], mode: str) -> str:
        initialize_earth_engine(self.auth, project_id=self.publish.project_id)
        import ee

        task_id = ee.data.newTaskId()[0]
        mode = mode.lower()
        if mode == "ingested":
            ee.data.startIngestion(task_id, manifest)
            return task_id

        if mode == "external_image":
            if hasattr(ee.data, "startExternalImageIngestion"):
                ee.data.startExternalImageIngestion(task_id, manifest)
                return task_id

            # Fallback for clients that only expose external image upload through CLI.
            manifest_path = Path("tmp") / f"external_manifest_{task_id}.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, indent=2))
            self._submit_with_cli(manifest_path, external=True)
            return task_id

        raise ValueError(f"Unsupported publish mode: {mode}")

    def submit_manifest_file(self, manifest_path: Path, mode: str) -> str:
        mode = mode.lower()
        if mode == "external_image":
            return self._submit_with_cli(manifest_path, external=True)
        return self._submit_with_cli(manifest_path, external=False)

    def poll_task(self, task_id: str, poll_interval_s: int, timeout_s: int) -> dict[str, Any]:
        initialize_earth_engine(self.auth, project_id=self.publish.project_id)
        import ee

        started = time.time()
        while True:
            status = ee.data.getTaskStatus(task_id)
            if isinstance(status, list):
                status = status[0] if status else {}
            state = status.get("state", "UNKNOWN")
            if state in {"SUCCEEDED", "FAILED", "CANCELLED", "COMPLETED"}:
                return status

            if time.time() - started > timeout_s:
                raise TimeoutError(f"Timed out waiting for Earth Engine task {task_id}")
            time.sleep(poll_interval_s)

    def set_asset_properties(self, asset_id: str, properties: dict[str, Any]) -> None:
        initialize_earth_engine(self.auth, project_id=self.publish.project_id)
        import ee

        if hasattr(ee.data, "setAssetProperties"):
            ee.data.setAssetProperties(asset_id, properties)
            return

        # CLI fallback if Python client lacks property setter.
        cmd = ["earthengine", "asset", "set"]
        for key, value in properties.items():
            cmd.extend(["--property", f"{key}={value}"])
        cmd.append(asset_id)
        subprocess.run(cmd, check=True)

    def publish_manifest(
        self,
        manifest: dict[str, Any],
        mode: str,
        asset_id: str,
        write_properties: bool = True,
    ) -> PublishResult:
        task_id = self.submit_manifest(manifest, mode=mode)
        status = self.poll_task(
            task_id,
            poll_interval_s=self.publish.task_poll_interval_s,
            timeout_s=self.publish.task_timeout_s,
        )
        state = status.get("state", "UNKNOWN")

        if write_properties and self.publish.write_asset_properties:
            props = manifest.get("properties", {})
            if props:
                self.set_asset_properties(asset_id, props)

        return PublishResult(asset_id=asset_id, task_id=task_id, state=state, details=status)

    def _submit_with_cli(self, manifest_path: Path, external: bool) -> str:
        command = ["earthengine", "upload", "external_image" if external else "image", "--manifest", str(manifest_path)]
        output = subprocess.check_output(command, text=True)
        for line in output.splitlines():
            lower = line.lower()
            if "task id" in lower:
                return line.split(":", 1)[-1].strip()
        return "unknown-task-id"
