"""The todo endpoints, called through FastAPI's test client against `create_app`."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService
from tests.fakes import TickingClock

UNKNOWN_ID = UUID(int=42)
ID_ROUTES = [
    pytest.param("GET", None, id="get"),
    pytest.param("PATCH", {"done": True}, id="patch"),
    pytest.param("DELETE", None, id="delete"),
]


@pytest.fixture
def service() -> TodoService:
    return TodoService(InMemoryTodoRepository(), clock=TickingClock())


@pytest.fixture
def client(service: TodoService) -> TestClient:
    return TestClient(create_app(service))


def _create(client: TestClient, title: str = "Buy milk") -> dict[str, Any]:
    response = client.post("/todos", json={"title": title})
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


def _get(client: TestClient, todo_id: object) -> dict[str, Any]:
    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def _complete(client: TestClient, todo_id: object) -> None:
    response = client.patch(f"/todos/{todo_id}", json={"done": True})
    assert response.status_code == 200


def _assert_only_detail(body: object, prefix: str = "") -> None:
    assert isinstance(body, dict)
    assert set(body) == {"detail"}
    assert isinstance(body["detail"], str)
    assert body["detail"].startswith(prefix)


def test_create_returns_the_new_open_todo(client: TestClient) -> None:
    response = client.post("/todos", json={"title": "Buy milk"})

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "title", "done", "created_at"}
    UUID(body["id"])
    assert body["title"] == "Buy milk"
    assert body["done"] is False
    created_at: str = body["created_at"]
    assert created_at.endswith(("Z", "+00:00"))
    assert datetime.fromisoformat(created_at).utcoffset() == timedelta(0)


def test_create_with_a_blank_title_is_rejected(client: TestClient) -> None:
    response = client.post("/todos", json={"title": "   "})

    assert response.status_code == 422
    assert response.json() == {"detail": "title must not be blank"}


@pytest.mark.parametrize(
    ("title", "status", "body"),
    [
        pytest.param("x" * 200, 201, None, id="200-chars"),
        pytest.param(
            "x" * 201, 422, {"detail": "title must be at most 200 characters"}, id="201-chars"
        ),
        pytest.param("  " + "x" * 200 + "  ", 201, None, id="200-chars-surrounded"),
    ],
)
def test_create_applies_the_title_length_limit(
    client: TestClient, title: str, status: int, body: dict[str, str] | None
) -> None:
    response = client.post("/todos", json={"title": title})

    assert response.status_code == status
    if body is not None:
        assert response.json() == body


def test_create_without_a_title_names_the_missing_field(client: TestClient) -> None:
    response = client.post("/todos", json={})

    assert response.status_code == 422
    assert response.json() == {"detail": "body.title: Field required"}


def test_create_strips_the_title(client: TestClient) -> None:
    response = client.post("/todos", json={"title": "  Buy milk "})

    assert response.status_code == 201
    assert response.json()["title"] == "Buy milk"


def test_list_returns_every_todo_in_creation_order(client: TestClient) -> None:
    created = [_create(client, title) for title in ("First", "Second", "Third")]

    response = client.get("/todos")

    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.parametrize(
    ("query", "done", "expected_titles"),
    [
        pytest.param("true", True, ["Done 1", "Done 2"], id="done"),
        pytest.param("false", False, ["Open 1", "Open 2"], id="open"),
    ],
)
def test_list_filters_by_the_done_flag(
    client: TestClient, query: str, done: bool, expected_titles: list[str]
) -> None:
    for title in ("Done 1", "Open 1", "Done 2", "Open 2"):
        todo = _create(client, title)
        if title.startswith("Done"):
            _complete(client, todo["id"])

    response = client.get(f"/todos?done={query}")

    assert response.status_code == 200
    listed = response.json()
    assert [todo["title"] for todo in listed] == expected_titles
    assert all(todo["done"] is done for todo in listed)


def test_list_with_an_invalid_done_filter_is_rejected(client: TestClient) -> None:
    response = client.get("/todos?done=maybe")

    assert response.status_code == 422
    _assert_only_detail(response.json(), "query.done: ")


def test_get_returns_the_todo(client: TestClient) -> None:
    _create(client, "Other")
    todo = _create(client, "Buy milk")

    response = client.get(f"/todos/{todo['id']}")

    assert response.status_code == 200
    assert response.json() == todo


@pytest.mark.parametrize(("method", "body"), ID_ROUTES)
def test_an_id_that_is_no_uuid_is_rejected(
    client: TestClient, method: str, body: dict[str, bool] | None
) -> None:
    response = client.request(method, "/todos/not-a-uuid", json=body)

    assert response.status_code == 422
    _assert_only_detail(response.json(), "path.todo_id: ")


def test_patch_done_completes_and_reopens_the_todo(client: TestClient) -> None:
    todo = _create(client)

    completed = client.patch(f"/todos/{todo['id']}", json={"done": True})

    assert completed.status_code == 200
    assert completed.json() == {**todo, "done": True}

    reopened = client.patch(f"/todos/{todo['id']}", json={"done": False})

    assert reopened.status_code == 200
    assert reopened.json() == {**todo, "done": False}


def test_patch_title_renames_the_todo_and_keeps_the_rest(client: TestClient) -> None:
    todo = _create(client)

    response = client.patch(f"/todos/{todo['id']}", json={"title": " New title "})

    assert response.status_code == 200
    assert response.json() == {**todo, "title": "New title"}


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="empty"),
        pytest.param({"title": None}, id="title-null"),
        pytest.param({"done": None}, id="done-null"),
        pytest.param({"title": None, "done": None}, id="both-null"),
    ],
)
def test_patch_that_sets_nothing_is_rejected_and_changes_nothing(
    client: TestClient, body: dict[str, None]
) -> None:
    todo = _create(client)

    response = client.patch(f"/todos/{todo['id']}", json=body)

    assert response.status_code == 422
    _assert_only_detail(response.json())
    assert _get(client, todo["id"]) == todo


def test_patch_with_a_blank_title_changes_nothing(client: TestClient) -> None:
    todo = _create(client, "Buy milk")

    response = client.patch(f"/todos/{todo['id']}", json={"title": "   ", "done": True})

    assert response.status_code == 422
    assert response.json() == {"detail": "title must not be blank"}
    after = _get(client, todo["id"])
    assert after["title"] == "Buy milk"
    assert after["done"] is False


def test_patch_title_and_done_applies_both(client: TestClient) -> None:
    todo = _create(client)

    response = client.patch(f"/todos/{todo['id']}", json={"title": " New title ", "done": True})

    assert response.status_code == 200
    assert response.json() == {**todo, "title": "New title", "done": True}
    assert _get(client, todo["id"]) == {**todo, "title": "New title", "done": True}


def test_delete_removes_the_todo(client: TestClient) -> None:
    todo = _create(client)

    response = client.delete(f"/todos/{todo['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/todos/{todo['id']}").status_code == 404


@pytest.mark.parametrize(("method", "body"), ID_ROUTES)
def test_an_unknown_id_is_not_found(
    client: TestClient, method: str, body: dict[str, bool] | None
) -> None:
    response = client.request(method, f"/todos/{UNKNOWN_ID}", json=body)

    assert response.status_code == 404
    assert response.json() == {"detail": "todo 00000000-0000-0000-0000-00000000002a not found"}


def test_routes_use_the_service_given_to_create_app(
    client: TestClient, service: TodoService
) -> None:
    todo = service.create("Buy milk")

    response = client.get("/todos")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(todo.id)]


def test_the_api_is_called_todo_service(service: TodoService) -> None:
    app = create_app(service)

    assert app.openapi()["info"]["title"] == "Todo service"


def test_each_app_uses_its_own_service() -> None:
    first = TodoService(InMemoryTodoRepository(), clock=TickingClock())
    second = TodoService(InMemoryTodoRepository(), clock=TickingClock())
    first_client = TestClient(create_app(first))
    second_client = TestClient(create_app(second))
    first.create("First")
    second.create("Second")

    assert [todo["title"] for todo in first_client.get("/todos").json()] == ["First"]
    assert [todo["title"] for todo in second_client.get("/todos").json()] == ["Second"]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        pytest.param("POST", "/todos", {"title": "   "}, id="blank-title"),
        pytest.param("POST", "/todos", {}, id="missing-title"),
        pytest.param("GET", "/todos?done=maybe", None, id="invalid-filter"),
        pytest.param("GET", "/todos/not-a-uuid", None, id="get-invalid-id"),
        pytest.param("PATCH", "/todos/not-a-uuid", {"done": True}, id="patch-invalid-id"),
        pytest.param("DELETE", "/todos/not-a-uuid", None, id="delete-invalid-id"),
        pytest.param("GET", f"/todos/{UNKNOWN_ID}", None, id="get-unknown-id"),
        pytest.param("PATCH", f"/todos/{UNKNOWN_ID}", {"done": True}, id="patch-unknown-id"),
        pytest.param("DELETE", f"/todos/{UNKNOWN_ID}", None, id="delete-unknown-id"),
    ],
)
def test_every_error_body_has_only_a_detail(
    client: TestClient, method: str, path: str, body: dict[str, object] | None
) -> None:
    response = client.request(method, path, json=body)

    assert response.status_code >= 400
    _assert_only_detail(response.json())
