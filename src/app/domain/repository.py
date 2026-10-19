"""The protocol every todo repository satisfies."""

from typing import Protocol
from uuid import UUID

from app.domain.model import Todo


class TodoRepository(Protocol):
    """Stores todos by id; lists them oldest first, equal times by id ascending."""

    def add(self, todo: Todo) -> None:
        """Store a new todo; raise `DuplicateTodo` if its id is already stored."""
        ...

    def get(self, todo_id: UUID) -> Todo:
        """Return the stored todo; raise `TodoNotFound` if there is none."""
        ...

    def list_all(self) -> list[Todo]:
        """Return every stored todo, by `created_at` then by id."""
        ...

    def update(self, todo: Todo) -> None:
        """Replace the stored todo with the same id; raise `TodoNotFound` if there is none."""
        ...

    def delete(self, todo_id: UUID) -> None:
        """Remove the stored todo; raise `TodoNotFound` if there is none."""
        ...
