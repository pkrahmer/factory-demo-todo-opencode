"""The `search` query parameter of `GET /todos`, called through the test client."""

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService
from tests.fakes import TickingClock
from tests.responses import assert_only_detail


@pytest.fixture
def service() -> TodoService:
    return TodoService(InMemoryTodoRepository(), clock=TickingClock())


@pytest.fixture
def client(service: TodoService) -> TestClient:
    return TestClient(create_app(service))


@pytest.fixture
def three_ids(service: TodoService) -> list[str]:
    return [str(service.create(title).id) for title in ("Buy Milk", "MILK run", "Call mum")]


@pytest.fixture
def milk_done_and_open(service: TodoService) -> None:
    bought = service.create("Buy Milk")
    service.create("MILK run")
    service.complete(bought.id)


def test_search_returns_the_matching_todos_in_creation_order(
    client: TestClient, three_ids: list[str]
) -> None:
    response = client.get("/todos", params={"search": "milk"})

    assert response.status_code == 200
    assert [todo["id"] for todo in response.json()] == three_ids[:2]


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
@pytest.mark.usefixtures("three_ids")
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
    client: TestClient, three_ids: list[str]
) -> None:
    response = client.get("/todos")

    assert response.status_code == 200
    assert [todo["id"] for todo in response.json()] == three_ids
