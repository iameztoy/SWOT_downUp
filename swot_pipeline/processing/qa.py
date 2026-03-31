from __future__ import annotations

import numpy as np


def apply_named_mask(
    arrays: dict[str, np.ndarray],
    mask_name: str | None,
    masks: dict[str, np.ndarray],
    skip_bands: set[str] | None = None,
) -> dict[str, np.ndarray]:
    if not mask_name:
        return arrays
    if mask_name not in masks:
        raise ValueError(f"Requested mask '{mask_name}' not found. Available masks: {sorted(masks)}")

    skip = skip_bands or set()
    out: dict[str, np.ndarray] = {}
    mask = masks[mask_name].astype(bool)
    for key, arr in arrays.items():
        if key in skip:
            out[key] = arr
            continue
        if np.issubdtype(arr.dtype, np.floating):
            out[key] = np.where(mask, arr, np.nan)
        else:
            # For integer QA or counts, set masked values to 0.
            out[key] = np.where(mask, arr, 0)
    return out
