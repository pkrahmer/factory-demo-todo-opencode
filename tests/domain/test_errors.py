"""The domain errors: their ids, their messages and their common base."""

from uuid import UUID

import pytest

from app.domain.errors import DuplicateTodo, InvalidTitle, TodoError, TodoNotFound

TODO_ID = UUID(int=7)


def test_todo_not_found_carries_the_id_and_names_it() -> None:
    error = TodoNotFound(TODO_ID)

    assert error.todo_id == TODO_ID
    assert str(error) == "todo 00000000-0000-0000-0000-000000000007 not found"


def test_duplicate_todo_carries_the_id_and_names_it() -> None:
    error = DuplicateTodo(TODO_ID)

    assert error.todo_id == TODO_ID
    assert str(error) == "todo 00000000-0000-0000-0000-000000000007 already exists"


@pytest.mark.parametrize("error_class", [InvalidTitle, TodoNotFound, DuplicateTodo])
def test_domain_errors_share_the_todo_error_base(error_class: type[Exception]) -> None:
    assert issubclass(error_class, TodoError)
