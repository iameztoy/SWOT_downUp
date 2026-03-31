from __future__ import annotations

from datetime import datetime

import requests

from swot_pipeline.models import AOIConfig, DataAccessConfig, GranuleRecord

CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"


def cmr_search(config: DataAccessConfig, date_start: datetime, date_end: datetime, aoi: AOIConfig) -> list[GranuleRecord]:
    records: list[GranuleRecord] = []
    page_num = 1

    while True:
        params = {
            "short_name": config.short_name,
            "page_size": config.page_size,
            "page_num": page_num,
            "temporal": f"{date_start.isoformat()},{date_end.isoformat()}",
        }
        if config.version:
            params["version"] = config.version
        if aoi.bbox:
            params["bounding_box"] = ",".join(str(v) for v in aoi.bbox)

        response = requests.get(CMR_GRANULES_URL, params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()
        entries = payload.get("feed", {}).get("entry", [])
        if not entries:
            break

        for item in entries:
            link = _best_data_link(item)
            if not link:
                continue
            record = GranuleRecord(
                granule_id=item.get("id", item.get("title", "unknown")),
                url=link,
                filename=item.get("title", link.split("/")[-1]),
                start_time=_parse_time(item.get("time_start")),
                end_time=_parse_time(item.get("time_end")),
                metadata={"cmr": item},
            )
            records.append(record)
            if config.max_results and len(records) >= config.max_results:
                return records

        page_num += 1

    return records


def _parse_time(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _best_data_link(entry: dict) -> str | None:
    links = entry.get("links", [])
    for link in links:
        href = link.get("href")
        if not href:
            continue
        rel = link.get("rel", "")
        title = (link.get("title") or "").lower()
        if "data#" in rel or "opendap" in rel or "download" in title:
            return href

    for link in links:
        href = link.get("href")
        if href:
            return href
    return None
