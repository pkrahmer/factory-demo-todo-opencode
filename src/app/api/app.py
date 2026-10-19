"""Builds the FastAPI application around a given service."""

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.service.todo_service import TodoService


def create_app(service: TodoService) -> FastAPI:
    app = FastAPI(title="Todo service")
    app.state.service = service
    app.include_router(router)
    register_error_handlers(app)
    return app
