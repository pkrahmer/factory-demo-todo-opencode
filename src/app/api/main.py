"""The composition root: the only place that chooses the concrete repository."""

from app.api.app import create_app
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService

app = create_app(TodoService(InMemoryTodoRepository()))
