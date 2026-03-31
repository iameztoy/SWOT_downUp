from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

_DATETIME_PATTERNS = [
    re.compile(r"(?P<ts>\d{8}T\d{6})"),
    re.compile(r"(?P<ts>\d{14})"),
]


def parse_datetime_from_filename(name: str | Path) -> datetime | None:
    text = Path(name).name
    for pattern in _DATETIME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        ts = match.group("ts")
        if "T" in ts:
            dt = datetime.strptime(ts, "%Y%m%dT%H%M%S")
        else:
            dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
        return dt.replace(tzinfo=timezone.utc)
    return None


def to_epoch_millis(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def to_rfc3339(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
