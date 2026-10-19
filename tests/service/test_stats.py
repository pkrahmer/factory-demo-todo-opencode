"""The todo counts the service computes from the repository's list."""

import dataclasses
from uuid import UUID

import pytest

from app.domain.model import Todo
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService, TodoStats
from tests.fakes import make_todo


class CountingRepository:
    """A `TodoRepository` around the in-memory one that records the name of every call."""

    def __init__(self, inner: InMemoryTodoRepository) -> None:
        self._inner = inner
        self.calls: list[str] = []

    def add(self, todo: Todo) -> None:
        self.calls.append("add")
        self._inner.add(todo)

    def get(self, todo_id: UUID) -> Todo:
        self.calls.append("get")
        return self._inner.get(todo_id)

    def list_all(self) -> list[Todo]:
        self.calls.append("list_all")
        return self._inner.list_all()

    def update(self, todo: Todo) -> None:
        self.calls.append("update")
        self._inner.update(todo)

    def delete(self, todo_id: UUID) -> None:
        self.calls.append("delete")
        self._inner.delete(todo_id)


@pytest.fixture
def two_open_one_done() -> InMemoryTodoRepository:
    repository = InMemoryTodoRepository()
    repository.add(make_todo(1, "Buy milk"))
    repository.add(make_todo(2, "Write the docs", done=True))
    repository.add(make_todo(3, "Call mum"))
    return repository


def test_stats_of_an_empty_repository_are_zero() -> None:
    stats = TodoService(InMemoryTodoRepository()).stats()

    assert stats == TodoStats(open=0, done=0)
    assert stats.total == 0


def test_stats_count_open_and_done_todos(two_open_one_done: InMemoryTodoRepository) -> None:
    stats = TodoService(two_open_one_done).stats()

    assert stats.open == 2
    assert stats.done == 1
    assert stats.total == 3


def test_stats_are_frozen() -> None:
    stats = TodoStats(open=1, done=0)
    field = "open"

    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(stats, field, 5)


def test_total_is_not_a_dataclass_field() -> None:
    names = [field.name for field in dataclasses.fields(TodoStats)]

    assert sorted(names) == ["done", "open"]


def test_stats_read_the_repository_with_one_list_all_call(
    two_open_one_done: InMemoryTodoRepository,
) -> None:
    repository = CountingRepository(two_open_one_done)
    service = TodoService(repository)

    service.stats()

    assert repository.calls == ["list_all"]
