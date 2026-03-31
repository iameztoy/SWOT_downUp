from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import numpy as np

from swot_pipeline.models import GranuleRecord, ProductPluginConfig
from swot_pipeline.utils.time import parse_datetime_from_filename


class ProductPlugin(ABC):
    plugin_name: str
    short_name: str
    version: str | None = None
    required_variables: list[str]
    optional_variables: list[str]
    supported_downloaders: list[str] = ["earthaccess", "podaac", "harmony"]

    def __init__(self, config: ProductPluginConfig):
        self.config = config

    def map_variable(self, variable: str) -> str:
        return self.config.variable_map.get(variable, variable)

    def parse_acquisition_time(self, granule: GranuleRecord) -> datetime:
        if granule.start_time:
            return granule.start_time

        dt = parse_datetime_from_filename(granule.filename)
        if dt is not None:
            return dt

        raise ValueError(f"Unable to infer acquisition time from granule {granule.filename}")

    def select_output_variables(self, explicit: list[str], optional: list[str]) -> list[str]:
        if explicit:
            return explicit
        bands = list(self.required_variables)
        for item in optional:
            if item in self.optional_variables and item not in bands:
                bands.append(item)
        return bands

    def get_metadata(self) -> dict[str, Any]:
        return {
            "plugin": self.plugin_name,
            "short_name": self.short_name,
            "version": self.version,
            "required_variables": list(self.required_variables),
            "optional_variables": list(self.optional_variables),
            "supported_downloaders": list(self.supported_downloaders),
            "preferred_output_bands": list(self.config.preferred_output_bands or self.required_variables),
        }

    @abstractmethod
    def build_quality_masks(
        self,
        extracted: dict[str, np.ndarray],
        quality_rules: dict[str, Any],
    ) -> dict[str, np.ndarray]:
        raise NotImplementedError
