"""A repository that keeps todos in a SQLite file through SQLAlchemy Core."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    Delete,
    Engine,
    Insert,
    MetaData,
    Row,
    String,
    Table,
    Update,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from app.domain.errors import DuplicateTodo, TodoNotFound
from app.domain.model import Todo

# Microseconds always written, offset always +00:00: every stored time has the same
# width, so the text order of `created_at` is its time order and the database can sort.
_CREATED_AT_FORMAT = "%Y-%m-%dT%H:%M:%S.%f+00:00"

_metadata = MetaData()

_todos = Table(
    "todos",
    _metadata,
    Column("id", String, primary_key=True),
    Column("title", String, nullable=False),
    Column("done", Boolean, nullable=False),
    Column("created_at", String, nullable=False),
)


def _stored_created_at(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime(_CREATED_AT_FORMAT)


def _with_todo_values[S: (Insert, Update)](statement: S, todo: Todo) -> S:
    return statement.values(
        id=str(todo.id),
        title=todo.title,
        done=todo.done,
        created_at=_stored_created_at(todo.created_at),
    )


def _todo_from_row(row: Row[Any]) -> Todo:
    return Todo(
        id=UUID(row.id),
        title=row.title,
        done=row.done,
        created_at=datetime.fromisoformat(row.created_at),
    )


class SqliteTodoRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        _metadata.create_all(engine, checkfirst=True)

    @classmethod
    def from_path(cls, path: str | Path) -> "SqliteTodoRepository":
        return cls(create_engine(f"sqlite:///{path}"))

    def add(self, todo: Todo) -> None:
        statement = _with_todo_values(insert(_todos), todo)
        try:
            with self._engine.begin() as connection:
                connection.execute(statement)
        except IntegrityError as error:
            raise DuplicateTodo(todo.id) from error

    def get(self, todo_id: UUID) -> Todo:
        statement = select(_todos).where(_todos.c.id == str(todo_id))
        with self._engine.connect() as connection:
            row = connection.execute(statement).one_or_none()
        if row is None:
            raise TodoNotFound(todo_id)
        return _todo_from_row(row)

    def list_all(self) -> list[Todo]:
        # The hyphenated UUID text has a fixed width, so its text order is the UUID order.
        statement = select(_todos).order_by(_todos.c.created_at, _todos.c.id)
        with self._engine.connect() as connection:
            rows = connection.execute(statement).all()
        return [_todo_from_row(row) for row in rows]

    def update(self, todo: Todo) -> None:
        statement = _with_todo_values(update(_todos).where(_todos.c.id == str(todo.id)), todo)
        self._execute_on_one_row(statement, todo.id)

    def delete(self, todo_id: UUID) -> None:
        statement = delete(_todos).where(_todos.c.id == str(todo_id))
        self._execute_on_one_row(statement, todo_id)

    def _execute_on_one_row(self, statement: Update | Delete, todo_id: UUID) -> None:
        with self._engine.begin() as connection:
            result = connection.execute(statement)
            if result.rowcount == 0:
                raise TodoNotFound(todo_id)
