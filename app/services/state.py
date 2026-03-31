from __future__ import annotations

from functools import lru_cache

from app.models.db import JobDatabase
from app.tasks.runner import JobRunner


@lru_cache(maxsize=1)
def get_db() -> JobDatabase:
    return JobDatabase()


@lru_cache(maxsize=1)
def get_runner() -> JobRunner:
    return JobRunner(db=get_db())
