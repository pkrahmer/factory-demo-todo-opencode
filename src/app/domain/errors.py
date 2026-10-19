"""The errors the domain raises when a rule or a lookup fails."""

from uuid import UUID


class TodoError(Exception):
    """Base of every error the domain raises."""


class InvalidTitle(TodoError):
    """A title is blank or longer than the allowed length."""


class TodoNotFound(TodoError):
    """No todo with the given id is stored."""

    def __init__(self, todo_id: UUID) -> None:
        """Name the id that was looked up."""
        super().__init__(f"todo {todo_id} not found")
        self.todo_id = todo_id


class DuplicateTodo(TodoError):
    """A todo with the given id is already stored."""

    def __init__(self, todo_id: UUID) -> None:
        """Name the id that is already taken."""
        super().__init__(f"todo {todo_id} already exists")
        self.todo_id = todo_id
