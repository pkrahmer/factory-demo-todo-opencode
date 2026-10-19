"""The todo use cases: create, read, list, rename, complete, reopen, delete and count."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.domain.model import Todo
from app.domain.repository import TodoRepository

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """Return the current time, timezone-aware in UTC."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class TodoStats:
    """How many todos are open and how many are done."""

    open: int
    done: int

    @property
    def total(self) -> int:
        """Return the number of all todos, open and done."""
        return self.open + self.done


class TodoService:
    """Runs the todo use cases against a repository, stamping new todos with a clock."""

    def __init__(self, repository: TodoRepository, clock: Clock = utc_now) -> None:
        """Use `repository` for storage and `clock` for creation times."""
        self._repository = repository
        self._clock = clock

    def create(self, title: str) -> Todo:
        """Store and return a new open todo created now; raise `InvalidTitle` for a bad title."""
        todo = Todo.new(title, now=self._clock())
        self._repository.add(todo)
        return todo

    def get(self, todo_id: UUID) -> Todo:
        """Return the todo; raise `TodoNotFound` if there is none."""
        return self._repository.get(todo_id)

    def list(self, *, done: bool | None = None) -> list[Todo]:
        """Return the todos in creation order; with `done` given, only those with that flag."""
        todos = self._repository.list_all()
        if done is None:
            return todos
        return [todo for todo in todos if todo.done is done]

    def stats(self) -> TodoStats:
        """Count the open and the done todos over one listing of the repository."""
        todos = self._repository.list_all()
        done = sum(1 for todo in todos if todo.done)
        return TodoStats(open=len(todos) - done, done=done)

    def rename(self, todo_id: UUID, title: str) -> Todo:
        """Give the todo another title and return it; raise `InvalidTitle` or `TodoNotFound`."""
        return self._store(self._repository.get(todo_id).with_title(title))

    def complete(self, todo_id: UUID) -> Todo:
        """Mark the todo done and return it; completing a done todo is allowed."""
        return self._store(self._repository.get(todo_id).with_done(True))

    def reopen(self, todo_id: UUID) -> Todo:
        """Mark the todo open and return it; reopening an open todo is allowed."""
        return self._store(self._repository.get(todo_id).with_done(False))

    def delete(self, todo_id: UUID) -> None:
        """Remove the todo; raise `TodoNotFound` if there is none."""
        self._repository.delete(todo_id)

    def _store(self, todo: Todo) -> Todo:
        self._repository.update(todo)
        return todo
