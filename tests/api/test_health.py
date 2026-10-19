"""The health endpoint and the composition root that tells it the storage kind."""

from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import NoReturn
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.main import build_app
from app.domain.model import Todo
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService

Environ = Callable[[Path], dict[str, str]]
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


class RaisingRepository:
    """A `TodoRepository` whose every method fails, standing in for a broken database."""

    def add(self, todo: Todo) -> NoReturn:
        del todo
        raise RuntimeError("storage is down")

    def get(self, todo_id: UUID) -> NoReturn:
        del todo_id
        raise RuntimeError("storage is down")

    def list_all(self) -> NoReturn:
        raise RuntimeError("storage is down")

    def update(self, todo: Todo) -> NoReturn:
        del todo
        raise RuntimeError("storage is down")

    def delete(self, todo_id: UUID) -> NoReturn:
        del todo_id
        raise RuntimeError("storage is down")


@pytest.fixture
def service() -> TodoService:
    return TodoService(InMemoryTodoRepository())


def test_health_reports_ok_version_and_memory_by_default(service: TodoService) -> None:
    response = TestClient(create_app(service)).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": version("app"), "storage": "memory"}


def test_health_reports_the_storage_given_to_create_app(service: TodoService) -> None:
    response = TestClient(create_app(service, storage="sqlite")).get("/health")

    assert response.status_code == 200
    assert response.json()["storage"] == "sqlite"


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        pytest.param(lambda _: {}, "memory", id="missing"),
        pytest.param(lambda _: {"TODO_DB": ""}, "memory", id="empty"),
        pytest.param(lambda p: {"TODO_DB": str(p)}, "sqlite", id="set"),
    ],
)
def test_build_app_reports_the_storage_the_environment_chose(
    db_path: Path, environ: Environ, expected: str
) -> None:
    response = TestClient(build_app(environ(db_path))).get("/health")

    assert response.status_code == 200
    assert response.json()["storage"] == expected


def test_health_does_not_touch_the_repository() -> None:
    client = TestClient(create_app(TodoService(RaisingRepository())), raise_server_exceptions=False)

    response = client.get("/health")

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("environ", "second_app_sees_it"),
    [
        pytest.param(lambda p: {"TODO_DB": str(p)}, True, id="sqlite"),
        pytest.param(lambda _: {}, False, id="memory"),
    ],
)
def test_build_app_hands_the_todo_routes_the_chosen_repository(
    db_path: Path, environ: Environ, second_app_sees_it: bool
) -> None:
    first = TestClient(build_app(environ(db_path)))
    created = first.post("/todos", json={"title": "Buy milk"})
    assert created.status_code == 201

    listed_by_first = first.get("/todos")
    listed_by_second = TestClient(build_app(environ(db_path))).get("/todos")

    assert listed_by_first.json() == [created.json()]
    assert listed_by_second.status_code == 200
    assert listed_by_second.json() == ([created.json()] if second_app_sees_it else [])


def test_schema_names_health_with_its_tag_beside_the_todo_paths(service: TodoService) -> None:
    paths = create_app(service).openapi()["paths"]

    assert "/health" in paths
    operations = [op for method, op in paths["/health"].items() if method in HTTP_METHODS]
    assert operations
    assert all("health" in op["tags"] for op in operations)
    assert "/todos" in paths
    assert "/todos/{todo_id}" in paths
