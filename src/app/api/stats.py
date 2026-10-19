"""The stats endpoint: how many todos are open, done and in total."""

from fastapi import APIRouter

from app.api.dependencies import Service
from app.api.schemas import StatsRead

router = APIRouter(tags=["stats"])


@router.get("/stats")
def read_stats(service: Service) -> StatsRead:
    return StatsRead.from_stats(service.stats())
