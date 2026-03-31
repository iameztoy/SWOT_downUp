from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from swot_pipeline.models import AOIConfig, DataAccessConfig, GranuleRecord


class DataAdapter(ABC):
    def __init__(self, config: DataAccessConfig):
        self.config = config

    @abstractmethod
    def search(
        self,
        date_start: datetime,
        date_end: datetime,
        aoi: AOIConfig,
    ) -> list[GranuleRecord]:
        raise NotImplementedError

    @abstractmethod
    def download(self, granules: list[GranuleRecord], output_dir: Path) -> list[GranuleRecord]:
        raise NotImplementedError
