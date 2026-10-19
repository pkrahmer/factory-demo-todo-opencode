"""The health endpoint a monitor polls; it never touches the repository."""

from importlib.metadata import version

from fastapi import APIRouter, Request

from app.api.schemas import HealthRead, StorageKind

router = APIRouter(tags=["health"])


@router.get("/health")
def read_health(request: Request) -> HealthRead:
    storage: StorageKind = request.app.state.storage
    return HealthRead(status="ok", version=version("app"), storage=storage)
