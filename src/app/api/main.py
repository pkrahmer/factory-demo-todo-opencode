"""The composition root: the only place that chooses the concrete repository."""

import os
from collections.abc import Mapping

from app.api.app import create_app
from app.domain.repository import TodoRepository
from app.repository.memory import InMemoryTodoRepository
from app.repository.sqlite import SqliteTodoRepository
from app.service.todo_service import TodoService


def build_repository(environ: Mapping[str, str]) -> TodoRepository:
    database_path = environ.get("TODO_DB", "")
    if not database_path:
        return InMemoryTodoRepository()
    return SqliteTodoRepository.from_path(database_path)


app = create_app(TodoService(build_repository(os.environ)))
