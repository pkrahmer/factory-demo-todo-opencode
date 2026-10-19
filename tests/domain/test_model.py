"""The Todo entity: its title rule, its UTC timestamp and its immutability."""

import dataclasses
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.domain.errors import InvalidTitle
from app.domain.model import Todo

T0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)

TitleBuilder = Callable[[str], Todo]
TimeBuilder = Callable[[datetime], Todo]


def _construct(title: str) -> Todo:
    return Todo(id=UUID(int=1), title=title, done=False, created_at=T0)


def _new(title: str) -> Todo:
    return Todo.new(title, now=T0)


def _with_title(title: str) -> Todo:
    return Todo.new("Original", now=T0).with_title(title)


TITLE_BUILDERS = [
    pytest.param(_construct, id="constructor"),
    pytest.param(_new, id="new"),
    pytest.param(_with_title, id="with_title"),
]


def _construct_at(created_at: datetime) -> Todo:
    return Todo(id=UUID(int=1), title="Buy milk", done=False, created_at=created_at)


def _new_at(created_at: datetime) -> Todo:
    return Todo.new("Buy milk", now=created_at)


TIME_BUILDERS = [
    pytest.param(_construct_at, id="constructor"),
    pytest.param(_new_at, id="new"),
]


@pytest.fixture
def todo() -> Todo:
    return Todo(id=UUID(int=1), title="Buy milk", done=False, created_at=T0)


def test_new_gives_an_open_todo_with_a_uuid4_id() -> None:
    created = Todo.new("Buy milk", now=T0)

    assert created.title == "Buy milk"
    assert created.done is False
    assert created.created_at == T0
    assert created.id.version == 4


def test_new_gives_a_fresh_id_on_every_call() -> None:
    first = Todo.new("Buy milk", now=T0)
    second = Todo.new("Buy milk", now=T0)

    assert first.id != second.id


@pytest.mark.parametrize("build", TITLE_BUILDERS)
def test_title_is_stripped_of_surrounding_whitespace(build: TitleBuilder) -> None:
    assert build("  Buy milk \n").title == "Buy milk"


@pytest.mark.parametrize("build", TITLE_BUILDERS)
@pytest.mark.parametrize("title", ["", "   ", "\n\t"])
def test_blank_title_is_rejected(build: TitleBuilder, title: str) -> None:
    with pytest.raises(InvalidTitle) as excinfo:
        build(title)

    assert str(excinfo.value) == "title must not be blank"


@pytest.mark.parametrize("build", TITLE_BUILDERS)
@pytest.mark.parametrize(
    ("title", "expected"),
    [
        pytest.param("x", "x", id="1-char"),
        pytest.param("x" * 200, "x" * 200, id="200-chars"),
        pytest.param("  x \n", "x", id="1-char-surrounded"),
        pytest.param(" \t" + "x" * 200 + "\n ", "x" * 200, id="200-chars-surrounded"),
        pytest.param("x" * 201, None, id="201-chars"),
    ],
)
def test_title_length_is_limited_to_200_characters(
    build: TitleBuilder, title: str, expected: str | None
) -> None:
    if expected is None:
        with pytest.raises(InvalidTitle) as excinfo:
            build(title)
        assert str(excinfo.value) == "title must be at most 200 characters"
    else:
        assert build(title).title == expected


@pytest.mark.parametrize("build", TIME_BUILDERS)
def test_created_at_is_converted_to_utc(build: TimeBuilder) -> None:
    local = datetime(2026, 10, 4, 14, 0, tzinfo=timezone(timedelta(hours=2)))

    created_at = build(local).created_at

    assert created_at == local
    assert created_at.utcoffset() == timedelta(0)


@pytest.mark.parametrize("build", TIME_BUILDERS)
def test_naive_created_at_is_rejected_with_value_error(build: TimeBuilder) -> None:
    with pytest.raises(ValueError) as excinfo:
        build(datetime(2026, 10, 4, 12, 0))

    assert not isinstance(excinfo.value, InvalidTitle)


def test_with_title_returns_a_new_todo_and_keeps_the_original(todo: Todo) -> None:
    renamed = todo.with_title("Buy bread")

    assert renamed.title == "Buy bread"
    assert renamed.id == todo.id
    assert renamed.done == todo.done
    assert renamed.created_at == todo.created_at
    assert todo.title == "Buy milk"


def test_with_done_returns_a_new_todo_and_keeps_the_original(todo: Todo) -> None:
    finished = todo.with_done(True)

    assert finished.done is True
    assert finished.id == todo.id
    assert finished.title == todo.title
    assert finished.created_at == todo.created_at
    assert todo.done is False


@pytest.mark.parametrize("field", ["id", "title", "done", "created_at"])
def test_todo_fields_cannot_be_assigned(todo: Todo, field: str) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(todo, field, "changed")
