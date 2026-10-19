"""The repository contract, run against every repository behind the protocol."""

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import pytest

from app.domain.errors import DuplicateTodo, TodoNotFound
from app.domain.model import Todo
from app.domain.repository import TodoRepository
from app.repository.memory import InMemoryTodoRepository
from app.repository.sqlite import SqliteTodoRepository
from tests.fakes import T0, make_todo

RepositoryFactory = Callable[[Path], TodoRepository]


def _in_memory(_: Path) -> TodoRepository:
    return InMemoryTodoRepository()


def _sqlite(tmp_path: Path) -> TodoRepository:
    return SqliteTodoRepository.from_path(tmp_path / "todo.db")


REPOSITORY_FACTORIES: list[RepositoryFactory] = [_in_memory, _sqlite]
REPOSITORY_CLASSES: list[type[object]] = [InMemoryTodoRepository, SqliteTodoRepository]


@pytest.fixture(params=REPOSITORY_FACTORIES)
def repository(request: pytest.FixtureRequest, tmp_path: Path) -> TodoRepository:
    factory: RepositoryFactory = request.param
    return factory(tmp_path)


def _get(repository: TodoRepository, todo: Todo) -> None:
    repository.get(todo.id)


def _update(repository: TodoRepository, todo: Todo) -> None:
    repository.update(todo)


def _delete(repository: TodoRepository, todo: Todo) -> None:
    repository.delete(todo.id)


def test_added_todo_can_be_read_back(repository: TodoRepository) -> None:
    todo = make_todo(1)

    repository.add(todo)

    assert repository.get(todo.id) == todo


def test_adding_a_stored_id_is_rejected(repository: TodoRepository) -> None:
    first = make_todo(1, "Buy milk")
    repository.add(first)

    with pytest.raises(DuplicateTodo) as excinfo:
        repository.add(make_todo(1, "Buy bread"))

    assert excinfo.value.todo_id == first.id
    assert repository.get(first.id) == first


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(_get, id="get"),
        pytest.param(_update, id="update"),
        pytest.param(_delete, id="delete"),
    ],
)
def test_unknown_id_is_not_found(
    repository: TodoRepository, operation: Callable[[TodoRepository, Todo], None]
) -> None:
    unknown = make_todo(42)

    with pytest.raises(TodoNotFound) as excinfo:
        operation(repository, unknown)

    assert excinfo.value.todo_id == unknown.id
    assert repository.list_all() == []


def test_empty_repository_lists_nothing(repository: TodoRepository) -> None:
    assert repository.list_all() == []


def test_todos_are_listed_oldest_first(repository: TodoRepository) -> None:
    oldest = make_todo(3, created_at=T0)
    middle = make_todo(1, created_at=T0 + timedelta(minutes=1))
    newest = make_todo(2, created_at=T0 + timedelta(minutes=2))
    for todo in (middle, newest, oldest):
        repository.add(todo)

    assert repository.list_all() == [oldest, middle, newest]


def test_todos_created_at_the_same_time_are_listed_by_id(repository: TodoRepository) -> None:
    first, second, third = make_todo(1), make_todo(2), make_todo(3)
    for todo in (third, first, second):
        repository.add(todo)

    assert repository.list_all() == [first, second, third]


def test_update_replaces_the_stored_todo(repository: TodoRepository) -> None:
    original = make_todo(1)
    repository.add(original)
    changed = original.with_title("Buy bread").with_done(True)

    repository.update(changed)

    assert repository.get(original.id) == changed


def test_deleted_todo_is_gone(repository: TodoRepository) -> None:
    todo = make_todo(1)
    repository.add(todo)

    repository.delete(todo.id)

    with pytest.raises(TodoNotFound):
        repository.get(todo.id)


@pytest.mark.parametrize("repository_class", REPOSITORY_CLASSES)
def test_repository_does_not_inherit_the_protocol(repository_class: type[object]) -> None:
    assert TodoRepository not in repository_class.__mro__
