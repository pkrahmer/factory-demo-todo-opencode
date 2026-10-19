"""The JSON bodies the API accepts and returns."""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.domain.model import Todo
from app.service.todo_service import TodoStats

StorageKind = Literal["memory", "sqlite"]


class TodoCreate(BaseModel):
    # No length or blank rule here: the domain strips the title first and owns the rule.
    title: str


class TodoUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None

    @model_validator(mode="after")
    def _sets_a_field(self) -> Self:
        if self.title is None and self.done is None:
            raise ValueError("set title or done")
        return self


class TodoRead(BaseModel):
    id: UUID
    title: str
    done: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, todo: Todo) -> "TodoRead":
        return cls(id=todo.id, title=todo.title, done=todo.done, created_at=todo.created_at)


class HealthRead(BaseModel):
    status: Literal["ok"]
    version: str
    storage: StorageKind


class StatsRead(BaseModel):
    open: int
    done: int
    total: int

    @classmethod
    def from_stats(cls, stats: TodoStats) -> "StatsRead":
        return cls(open=stats.open, done=stats.done, total=stats.total)
