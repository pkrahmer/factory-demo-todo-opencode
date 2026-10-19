"""The composition root chooses the repository from the environment."""

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.main import build_repository
from app.repository.memory import InMemoryTodoRepository
from app.repository.sqlite import SqliteTodoRepository
from app.service.todo_service import TodoService

Environ = Callable[[Path], dict[str, str]]


def _client(environ: dict[str, str]) -> TestClient:
    return TestClient(create_app(TodoService(build_repository(environ))))


@pytest.mark.parametrize(
    ("environ", "expected", "creates_file"),
    [
        pytest.param(lambda _: {}, InMemoryTodoRepository, False, id="missing"),
        pytest.param(lambda _: {"TODO_DB": ""}, InMemoryTodoRepository, False, id="empty"),
        pytest.param(lambda p: {"TODO_DB": str(p)}, SqliteTodoRepository, True, id="set"),
    ],
)
def test_todo_db_chooses_the_repository(
    db_path: Path, environ: Environ, expected: type[object], creates_file: bool
) -> None:
    repository = build_repository(environ(db_path))

    assert isinstance(repository, expected)
    if creates_file:
        assert db_path.is_file()


def test_todos_persist_across_apps_on_the_same_file(db_path: Path) -> None:
    environ = {"TODO_DB": str(db_path)}
    created = _client(environ).post("/todos", json={"title": "Survive a restart"})
    assert created.status_code == 201

    listed = _client(environ).get("/todos")

    assert listed.status_code == 200
    assert listed.json() == [created.json()]


def test_in_memory_app_writes_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = _client({})

    response = client.post("/todos", json={"title": "Buy milk"})

    assert response.status_code == 201
    assert list(tmp_path.iterdir()) == []
