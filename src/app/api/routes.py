"""The todo endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import Service
from app.api.schemas import TodoCreate, TodoRead, TodoUpdate
from app.domain.model import MAX_TITLE_LENGTH

router = APIRouter(prefix="/todos", tags=["todos"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_todo(body: TodoCreate, service: Service) -> TodoRead:
    return TodoRead.from_domain(service.create(body.title))


@router.get("")
def list_todos(
    service: Service,
    done: bool | None = None,
    search: Annotated[str | None, Query(max_length=MAX_TITLE_LENGTH)] = None,
) -> list[TodoRead]:
    return [TodoRead.from_domain(todo) for todo in service.list(done=done, search=search)]


@router.get("/{todo_id}")
def get_todo(todo_id: UUID, service: Service) -> TodoRead:
    return TodoRead.from_domain(service.get(todo_id))


@router.patch("/{todo_id}")
def update_todo(todo_id: UUID, body: TodoUpdate, service: Service) -> TodoRead:
    # The title goes first, so an invalid title leaves the done flag untouched as well.
    todo = service.get(todo_id) if body.title is None else service.rename(todo_id, body.title)
    if body.done is not None:
        todo = service.complete(todo_id) if body.done else service.reopen(todo_id)
    return TodoRead.from_domain(todo)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: UUID, service: Service) -> None:
    service.delete(todo_id)
