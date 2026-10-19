"""The composition root: the only place that chooses the concrete repository."""

import os
from collections.abc import Mapping

from fastapi import FastAPI

from app.api.app import create_app
from app.api.schemas import StorageKind
from app.domain.repository import TodoRepository
from app.repository.memory import InMemoryTodoRepository
from app.repository.sqlite import SqliteTodoRepository
from app.service.todo_service import TodoService


def _storage_kind(environ: Mapping[str, str]) -> StorageKind:
    return "sqlite" if environ.get("TODO_DB", "") else "memory"


def build_repository(environ: Mapping[str, str]) -> TodoRepository:
    if _storage_kind(environ) == "memory":
        return InMemoryTodoRepository()
    return SqliteTodoRepository.from_path(environ["TODO_DB"])


def build_app(environ: Mapping[str, str]) -> FastAPI:
    service = TodoService(build_repository(environ))
    return create_app(service, storage=_storage_kind(environ))


app = build_app(os.environ)
