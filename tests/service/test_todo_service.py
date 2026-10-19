"""The use cases of the todo service, run against the in-memory repository."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.domain.errors import InvalidTitle, TodoNotFound
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService, utc_now

T0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
UNKNOWN_ID = UUID(int=42)
BLANK_TITLES = [pytest.param("", id="empty"), pytest.param("   ", id="spaces")]


class TickingClock:
    """A clock that starts at T0 and moves a minute ahead on every call."""

    def __init__(self) -> None:
        self._calls = 0

    def __call__(self) -> datetime:
        moment = T0 + timedelta(minutes=self._calls)
        self._calls += 1
        return moment


@pytest.fixture
def service() -> TodoService:
    return TodoService(InMemoryTodoRepository(), clock=lambda: T0)


@pytest.fixture
def ticking_service() -> TodoService:
    return TodoService(InMemoryTodoRepository(), clock=TickingClock())


def _assert_utc_close_to_now(moment: datetime) -> None:
    assert moment.utcoffset() == timedelta(0)
    assert abs(moment - datetime.now(UTC)) <= timedelta(seconds=1)


def test_create_strips_the_title_and_stamps_the_clock(service: TodoService) -> None:
    todo = service.create("  Buy milk ")

    assert todo.title == "Buy milk"
    assert todo.done is False
    assert todo.created_at == T0
    assert service.get(todo.id) == todo


@pytest.mark.parametrize("title", BLANK_TITLES)
def test_create_with_a_blank_title_is_rejected_and_stores_nothing(
    service: TodoService, title: str
) -> None:
    with pytest.raises(InvalidTitle):
        service.create(title)

    assert service.list() == []


def test_get_with_an_unknown_id_is_not_found(service: TodoService) -> None:
    with pytest.raises(TodoNotFound) as excinfo:
        service.get(UNKNOWN_ID)

    assert excinfo.value.todo_id == UNKNOWN_ID


def test_list_returns_every_todo_in_creation_order(ticking_service: TodoService) -> None:
    created = [ticking_service.create(title) for title in ("First", "Second", "Third")]

    assert ticking_service.list() == created


@pytest.mark.parametrize(
    ("done", "expected_titles"),
    [
        pytest.param(True, ["Done 1", "Done 2"], id="done"),
        pytest.param(False, ["Open 1", "Open 2"], id="open"),
        pytest.param(None, ["Done 1", "Open 1", "Done 2", "Open 2"], id="all"),
    ],
)
def test_list_filters_by_the_done_flag(
    ticking_service: TodoService, done: bool | None, expected_titles: list[str]
) -> None:
    for title in ("Done 1", "Open 1", "Done 2", "Open 2"):
        todo = ticking_service.create(title)
        if title.startswith("Done"):
            ticking_service.complete(todo.id)

    listed = ticking_service.list(done=done)

    assert [todo.title for todo in listed] == expected_titles


def test_rename_changes_only_the_title(service: TodoService) -> None:
    original = service.create("Buy milk")
    service.complete(original.id)

    renamed = service.rename(original.id, "  Buy bread ")

    assert renamed.title == "Buy bread"
    assert renamed.id == original.id
    assert renamed.done is True
    assert renamed.created_at == original.created_at
    assert service.get(original.id) == renamed


@pytest.mark.parametrize("title", BLANK_TITLES)
def test_rename_with_a_blank_title_is_rejected_and_keeps_the_old_title(
    service: TodoService, title: str
) -> None:
    original = service.create("Buy milk")

    with pytest.raises(InvalidTitle):
        service.rename(original.id, title)

    assert service.get(original.id).title == "Buy milk"


def test_complete_marks_the_todo_done(service: TodoService) -> None:
    todo = service.create("Buy milk")

    completed = service.complete(todo.id)

    assert completed.done is True
    assert service.get(todo.id).done is True


def test_completing_a_completed_todo_keeps_it_done(service: TodoService) -> None:
    todo = service.create("Buy milk")
    service.complete(todo.id)

    again = service.complete(todo.id)

    assert again.id == todo.id
    assert again.done is True


def test_reopen_marks_the_todo_open(service: TodoService) -> None:
    todo = service.create("Buy milk")
    service.complete(todo.id)

    reopened = service.reopen(todo.id)

    assert reopened.done is False
    assert service.get(todo.id).done is False


def test_reopening_an_open_todo_keeps_it_open(service: TodoService) -> None:
    todo = service.create("Buy milk")

    again = service.reopen(todo.id)

    assert again.id == todo.id
    assert again.done is False


def test_delete_removes_the_todo(service: TodoService) -> None:
    todo = service.create("Buy milk")

    service.delete(todo.id)

    with pytest.raises(TodoNotFound):
        service.get(todo.id)


def _rename(service: TodoService, todo_id: UUID) -> None:
    service.rename(todo_id, "Buy bread")


def _complete(service: TodoService, todo_id: UUID) -> None:
    service.complete(todo_id)


def _reopen(service: TodoService, todo_id: UUID) -> None:
    service.reopen(todo_id)


def _delete(service: TodoService, todo_id: UUID) -> None:
    service.delete(todo_id)


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(_rename, id="rename"),
        pytest.param(_complete, id="complete"),
        pytest.param(_reopen, id="reopen"),
        pytest.param(_delete, id="delete"),
    ],
)
def test_changing_an_unknown_id_is_not_found(
    service: TodoService, operation: Callable[[TodoService, UUID], None]
) -> None:
    with pytest.raises(TodoNotFound) as excinfo:
        operation(service, UNKNOWN_ID)

    assert excinfo.value.todo_id == UNKNOWN_ID


def test_utc_now_is_the_current_time_in_utc() -> None:
    now = utc_now()

    _assert_utc_close_to_now(now)


def test_service_without_a_clock_stamps_the_current_utc_time() -> None:
    service = TodoService(InMemoryTodoRepository())

    todo = service.create("Buy milk")

    _assert_utc_close_to_now(todo.created_at)
