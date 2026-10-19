"""A repository that keeps todos in a dictionary, for as long as the process runs."""

from uuid import UUID

from app.domain.errors import DuplicateTodo, TodoNotFound
from app.domain.model import Todo


class InMemoryTodoRepository:
    def __init__(self) -> None:
        self._todos: dict[UUID, Todo] = {}

    def add(self, todo: Todo) -> None:
        if todo.id in self._todos:
            raise DuplicateTodo(todo.id)
        self._todos[todo.id] = todo

    def get(self, todo_id: UUID) -> Todo:
        self._require(todo_id)
        return self._todos[todo_id]

    def list_all(self) -> list[Todo]:
        return sorted(self._todos.values(), key=lambda todo: (todo.created_at, todo.id))

    def update(self, todo: Todo) -> None:
        self._require(todo.id)
        self._todos[todo.id] = todo

    def delete(self, todo_id: UUID) -> None:
        self._require(todo_id)
        del self._todos[todo_id]

    def _require(self, todo_id: UUID) -> None:
        if todo_id not in self._todos:
            raise TodoNotFound(todo_id)
