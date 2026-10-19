"""Builds the FastAPI application around a given service."""

from fastapi import FastAPI

from app.api import health, stats
from app.api.errors import register_error_handlers
from app.api.routes import router
from app.api.schemas import StorageKind
from app.service.todo_service import TodoService


def create_app(service: TodoService, *, storage: StorageKind = "memory") -> FastAPI:
    app = FastAPI(title="Todo service")
    app.state.service = service
    app.state.storage = storage
    app.include_router(router)
    app.include_router(health.router)
    app.include_router(stats.router)
    register_error_handlers(app)
    return app
