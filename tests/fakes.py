"""Test doubles shared by the test modules of several layers."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.domain.model import Todo

T0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


class TickingClock:
    """A clock that starts at T0 and moves a minute ahead on every call."""

    def __init__(self) -> None:
        self._calls = 0

    def __call__(self) -> datetime:
        moment = T0 + timedelta(minutes=self._calls)
        self._calls += 1
        return moment


def make_todo(
    n: int, title: str = "Buy milk", *, done: bool = False, created_at: datetime = T0
) -> Todo:
    """Build a todo with the fixed id `UUID(int=n)`."""
    return Todo(id=UUID(int=n), title=title, done=done, created_at=created_at)
