"""Listing todos by a piece of their title through the todo service."""

import pytest

from app.domain.model import Todo
from app.service.todo_service import TodoService


def test_search_returns_the_todos_whose_title_contains_the_text_in_creation_order(
    ticking_service: TodoService, three_todos: list[Todo]
) -> None:
    assert ticking_service.list(search="milk") == three_todos[:2]


@pytest.mark.usefixtures("three_todos")
def test_search_text_is_stripped(ticking_service: TodoService) -> None:
    assert ticking_service.list(search="  milk ") == ticking_service.list(search="milk")


@pytest.mark.usefixtures("three_todos")
@pytest.mark.parametrize(
    "search",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="spaces"),
    ],
)
def test_no_or_blank_search_means_no_title_filter(
    ticking_service: TodoService, search: str | None
) -> None:
    assert ticking_service.list(search=search) == ticking_service.list()


def test_search_uses_case_folding(ticking_service: TodoService) -> None:
    todo = ticking_service.create("Straße")

    assert ticking_service.list(search="STRASSE") == [todo]


@pytest.mark.parametrize(
    ("done", "expected_titles"),
    [
        pytest.param(False, ["MILK run"], id="open"),
        pytest.param(True, ["Buy Milk"], id="done"),
    ],
)
@pytest.mark.usefixtures("milk_done_and_open")
def test_search_combines_with_the_done_filter(
    ticking_service: TodoService, done: bool, expected_titles: list[str]
) -> None:
    listed = ticking_service.list(done=done, search="milk")

    assert [todo.title for todo in listed] == expected_titles
