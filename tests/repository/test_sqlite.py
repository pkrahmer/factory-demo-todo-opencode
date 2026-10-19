"""The SQLite repository: persistence across instances and the stored format."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import MetaData, Table, create_engine, select

from app.repository.sqlite import SqliteTodoRepository
from tests.fakes import T0, make_todo

PathForm = Callable[[Path], str | Path]


def _as_path(path: Path) -> str | Path:
    return path


def _as_str(path: Path) -> str | Path:
    return str(path)


def test_from_path_creates_a_missing_file_and_starts_empty(db_path: Path) -> None:
    assert not db_path.exists()

    repository = SqliteTodoRepository.from_path(db_path)

    assert db_path.is_file()
    assert repository.list_all() == []


def test_todo_is_seen_by_a_second_instance_on_the_same_path(db_path: Path) -> None:
    todo = make_todo(1)
    SqliteTodoRepository.from_path(db_path).add(todo)

    second = SqliteTodoRepository.from_path(db_path)

    assert second.get(todo.id) == todo
    assert second.list_all() == [todo]


def test_second_instance_on_the_same_engine_keeps_the_stored_todos(db_path: Path) -> None:
    engine = create_engine(f"sqlite:///{db_path}")
    todo = make_todo(1)
    SqliteTodoRepository(engine).add(todo)

    second = SqliteTodoRepository(engine)

    assert second.list_all() == [todo]


def test_created_at_survives_the_round_trip(db_path: Path) -> None:
    created_at = datetime(2026, 10, 4, 12, 0, 0, 123456, tzinfo=UTC)
    todo = make_todo(1, created_at=created_at)
    SqliteTodoRepository.from_path(db_path).add(todo)

    read_back = SqliteTodoRepository.from_path(db_path).get(todo.id).created_at

    assert read_back == created_at
    assert read_back.tzinfo is not None
    assert read_back.utcoffset() == timedelta(0)


def test_title_with_quotes_and_sql_is_stored_verbatim(db_path: Path) -> None:
    repository = SqliteTodoRepository.from_path(db_path)
    before = make_todo(1, "Buy milk", created_at=T0)
    hostile = make_todo(2, "Robert'); DROP TABLE todos;--", created_at=T0 + timedelta(minutes=1))
    after = make_todo(3, "Buy bread", created_at=T0 + timedelta(minutes=2))
    repository.add(before)
    repository.add(hostile)
    repository.add(after)

    assert repository.get(hostile.id).title == "Robert'); DROP TABLE todos;--"
    assert repository.list_all() == [before, hostile, after]


@pytest.mark.parametrize(
    ("done", "created_at"),
    [
        pytest.param(False, T0, id="open-utc"),
        pytest.param(True, T0, id="done-utc"),
        pytest.param(
            False,
            datetime(2026, 10, 4, 14, 0, 0, 123456, tzinfo=timezone(timedelta(hours=2))),
            id="open-other-offset",
        ),
    ],
)
def test_stored_row_has_the_documented_format(
    db_path: Path, done: bool, created_at: datetime
) -> None:
    engine = create_engine(f"sqlite:///{db_path}")
    todo = make_todo(1, done=done, created_at=created_at)
    SqliteTodoRepository(engine).add(todo)

    todos = Table("todos", MetaData(), autoload_with=engine)
    with engine.connect() as connection:
        rows = connection.execute(select(todos)).mappings().all()

    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == str(todo.id)
    stored_created_at = row["created_at"]
    assert isinstance(stored_created_at, str)
    assert stored_created_at.endswith("+00:00")
    assert datetime.fromisoformat(stored_created_at) == todo.created_at
    assert isinstance(row["done"], bool)
    assert row["done"] is done


@pytest.mark.parametrize(
    ("write_form", "read_form"),
    [
        pytest.param(_as_path, _as_str, id="path-then-str"),
        pytest.param(_as_str, _as_path, id="str-then-path"),
    ],
)
def test_path_and_str_open_the_same_file(
    db_path: Path, write_form: PathForm, read_form: PathForm
) -> None:
    todo = make_todo(1)
    SqliteTodoRepository.from_path(write_form(db_path)).add(todo)

    assert SqliteTodoRepository.from_path(read_form(db_path)).list_all() == [todo]
