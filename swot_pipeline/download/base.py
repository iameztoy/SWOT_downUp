from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from swot_pipeline.models import AOIConfig, GranuleRecord, PipelineConfig


class DownloaderAdapter(ABC):
    name: str
    display_name: str

    def __init__(self, pipeline_config: PipelineConfig):
        self.pipeline_config = pipeline_config

    @abstractmethod
    def search(self, date_start: datetime, date_end: datetime, aoi: AOIConfig) -> list[GranuleRecord]:
        raise NotImplementedError

    @abstractmethod
    def download(self, granules: list[GranuleRecord], output_dir: Path) -> list[GranuleRecord]:
        raise NotImplementedError

    @abstractmethod
    def validate_config(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        raise NotImplementedError
