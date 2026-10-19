"""Listing todos by a piece of their title through the todo service."""

import pytest

from app.domain.model import Todo
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService
from tests.fakes import TickingClock


@pytest.fixture
def service() -> TodoService:
    return TodoService(InMemoryTodoRepository(), clock=TickingClock())


@pytest.fixture
def three_todos(service: TodoService) -> list[Todo]:
    return [service.create(title) for title in ("Buy Milk", "MILK run", "Call mum")]


@pytest.fixture
def milk_done_and_open(service: TodoService) -> None:
    bought = service.create("Buy Milk")
    service.create("MILK run")
    service.complete(bought.id)


def test_search_returns_the_todos_whose_title_contains_the_text_in_creation_order(
    service: TodoService, three_todos: list[Todo]
) -> None:
    assert service.list(search="milk") == three_todos[:2]


@pytest.mark.usefixtures("three_todos")
def test_search_text_is_stripped(service: TodoService) -> None:
    assert service.list(search="  milk ") == service.list(search="milk")


@pytest.mark.usefixtures("three_todos")
@pytest.mark.parametrize(
    "search",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="spaces"),
    ],
)
def test_no_or_blank_search_means_no_title_filter(service: TodoService, search: str | None) -> None:
    assert service.list(search=search) == service.list()


def test_search_uses_case_folding(service: TodoService) -> None:
    todo = service.create("Straße")

    assert service.list(search="STRASSE") == [todo]


@pytest.mark.parametrize(
    ("done", "expected_titles"),
    [
        pytest.param(False, ["MILK run"], id="open"),
        pytest.param(True, ["Buy Milk"], id="done"),
    ],
)
@pytest.mark.usefixtures("milk_done_and_open")
def test_search_combines_with_the_done_filter(
    service: TodoService, done: bool, expected_titles: list[str]
) -> None:
    listed = service.list(done=done, search="milk")

    assert [todo.title for todo in listed] == expected_titles
