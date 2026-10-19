"""Fixtures shared by the test modules of several layers."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.domain.model import Todo
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService
from tests.fakes import TickingClock


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """A path under `tmp_path` where no SQLite file exists yet."""
    return tmp_path / "todo.db"


@pytest.fixture
def ticking_service() -> TodoService:
    """A service over an empty in-memory repository whose clock ticks on each call."""
    return TodoService(InMemoryTodoRepository(), clock=TickingClock())


@pytest.fixture
def client(ticking_service: TodoService) -> TestClient:
    """A test client of the app built around `ticking_service`."""
    return TestClient(create_app(ticking_service))


@pytest.fixture
def three_todos(ticking_service: TodoService) -> list[Todo]:
    """`Buy Milk`, `MILK run` and `Call mum`, created in that order, all open."""
    return [ticking_service.create(title) for title in ("Buy Milk", "MILK run", "Call mum")]


@pytest.fixture
def milk_done_and_open(ticking_service: TodoService) -> None:
    """`Buy Milk`, done, then `MILK run`, open."""
    bought = ticking_service.create("Buy Milk")
    ticking_service.create("MILK run")
    ticking_service.complete(bought.id)
