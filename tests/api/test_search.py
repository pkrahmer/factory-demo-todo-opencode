"""The `search` query parameter of `GET /todos`, called through the test client."""

import pytest
from fastapi.testclient import TestClient

from app.domain.model import Todo
from tests.responses import assert_only_detail


def test_search_returns_the_matching_todos_in_creation_order(
    client: TestClient, three_todos: list[Todo]
) -> None:
    response = client.get("/todos", params={"search": "milk"})

    assert response.status_code == 200
    assert [todo["id"] for todo in response.json()] == [str(todo.id) for todo in three_todos[:2]]


@pytest.mark.usefixtures("milk_done_and_open")
def test_search_combines_with_the_done_filter(client: TestClient) -> None:
    response = client.get("/todos", params={"done": "true", "search": "milk"})

    assert response.status_code == 200
    assert [todo["title"] for todo in response.json()] == ["Buy Milk"]


@pytest.mark.parametrize(
    ("search", "status"),
    [
        pytest.param("x" * 200, 200, id="200-chars"),
        pytest.param("x" * 201, 422, id="201-chars"),
        pytest.param(" " * 197 + "milk", 422, id="201-chars-padded"),
    ],
)
@pytest.mark.usefixtures("three_todos")
def test_search_length_is_limited_on_the_text_as_sent(
    client: TestClient, search: str, status: int
) -> None:
    response = client.get("/todos", params={"search": search})

    assert response.status_code == status
    if status == 200:
        assert response.json() == []
    else:
        assert_only_detail(response.json(), "query.search: ")


def test_list_without_parameters_returns_every_todo(
    client: TestClient, three_todos: list[Todo]
) -> None:
    response = client.get("/todos")

    assert response.status_code == 200
    assert [todo["id"] for todo in response.json()] == [str(todo.id) for todo in three_todos]
