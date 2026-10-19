"""The stats endpoint, called through FastAPI's test client against `create_app`."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.main import app
from app.service.todo_service import TodoService
from tests.fakes import HTTP_METHODS


def _nothing(service: TodoService) -> None:
    del service


def _two_open_one_done(service: TodoService) -> None:
    service.create("Buy milk")
    service.complete(service.create("Write the docs").id)
    service.create("Call mum")


@pytest.mark.parametrize(
    ("seed", "expected"),
    [
        pytest.param(_two_open_one_done, {"open": 2, "done": 1, "total": 3}, id="mixed"),
        pytest.param(_nothing, {"open": 0, "done": 0, "total": 0}, id="empty"),
    ],
)
def test_get_stats_returns_the_counts(
    ticking_service: TodoService, seed: Callable[[TodoService], None], expected: dict[str, int]
) -> None:
    seed(ticking_service)

    response = TestClient(create_app(ticking_service)).get("/stats")

    assert response.status_code == 200
    assert response.json() == expected


def test_schema_names_stats_with_its_tag_beside_the_other_paths() -> None:
    paths = app.openapi()["paths"]

    assert "/stats" in paths
    operations = [op for method, op in paths["/stats"].items() if method in HTTP_METHODS]
    assert operations
    assert all("stats" in op["tags"] for op in operations)
    for path in ("/todos", "/todos/{todo_id}", "/health"):
        assert path in paths
