from __future__ import annotations

from swot_pipeline.download import list_downloaders


def get_downloaders() -> list[dict[str, object]]:
    return list_downloaders()
