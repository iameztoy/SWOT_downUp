from __future__ import annotations

from pathlib import Path

import xarray as xr


def open_dataset_lazy(path: str | Path) -> xr.Dataset:
    # Prefer lazy reads via dask-style chunking, but fall back when dask is unavailable.
    try:
        return xr.open_dataset(path, chunks={}, decode_cf=True, mask_and_scale=True)
    except ValueError as exc:
        # xarray raises ValueError if chunked loading is requested without an installed chunk backend.
        if "chunk manager" not in str(exc).lower():
            raise
        return xr.open_dataset(path, decode_cf=True, mask_and_scale=True)
