"""Hands each route the service of the app it belongs to."""

from typing import Annotated

from fastapi import Depends, Request

from app.service.todo_service import TodoService


def get_service(request: Request) -> TodoService:
    service: TodoService = request.app.state.service
    return service


Service = Annotated[TodoService, Depends(get_service)]
