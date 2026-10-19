"""The Todo entity and the rules that hold however a todo is built."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.errors import InvalidTitle

MAX_TITLE_LENGTH = 200


def _normalized_title(title: str) -> str:
    stripped = title.strip()
    if not stripped:
        raise InvalidTitle("title must not be blank")
    if len(stripped) > MAX_TITLE_LENGTH:
        raise InvalidTitle(f"title must be at most {MAX_TITLE_LENGTH} characters")
    return stripped


def _in_utc(moment: datetime) -> datetime:
    if moment.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    return moment.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Todo:
    """A single to-do: a stripped title, a done flag and its UTC creation time."""

    id: UUID
    title: str
    done: bool
    created_at: datetime

    def __post_init__(self) -> None:
        """Strip and check the title, and convert the creation time to UTC."""
        # The dataclass is frozen, so normalising a field bypasses its own __setattr__.
        object.__setattr__(self, "title", _normalized_title(self.title))
        object.__setattr__(self, "created_at", _in_utc(self.created_at))

    @classmethod
    def new(cls, title: str, *, now: datetime) -> "Todo":
        """Create an open todo with a fresh random id, created at `now`."""
        return cls(id=uuid4(), title=title, done=False, created_at=now)

    def with_title(self, title: str) -> "Todo":
        """Return a copy of this todo with another title."""
        return replace(self, title=title)

    def with_done(self, done: bool) -> "Todo":
        """Return a copy of this todo with another done flag."""
        return replace(self, done=done)
