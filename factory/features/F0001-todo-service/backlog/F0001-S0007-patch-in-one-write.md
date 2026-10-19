# PATCH with title and done in one write

<!-- proposed by feature acceptance of 2026-10-19; refine before starting -->

## Description

`PATCH /todos/{id}` with both `title` and `done` calls `rename` and then `complete` or `reopen`. Each call reads the todo and writes it back, so the request makes two writes against the repository. S0003's coder left this open, and S0004's documenter wrote it into `docs/api.md`: "with SQLite a failure between the two writes can leave the rename applied without the `done` change. It is worth revisiting." This story adds a service use case that applies both changes to one read of the todo and stores the result with one `update`. `PATCH` then uses it for every body, so a request changes either everything it asks for or nothing. The rules a client sees stay the same: title first, an invalid title changes nothing, completing a completed todo is not an error, and a body that sets neither field is a 422 in the schema. `rename`, `complete` and `reopen` stay as they are.

## Interface

`src/app/service/todo_service.py`

```python
class TodoService:
    def change(self, todo_id: UUID, *, title: str | None = None, done: bool | None = None) -> Todo: ...
```

- `change` reads the todo once and applies `title` (when given) and then `done` (when given). It stores the result with exactly one `update` call and returns it.
- With neither given, it returns the stored todo and does not call `update`.
- An invalid title raises `InvalidTitle` before any `update`. An unknown id raises `TodoNotFound` carrying that id.

`src/app/api/routes.py`: `update_todo` calls `service.change(todo_id, title=body.title, done=body.done)` and nothing else of the service.

Tests: `tests/service/test_todo_service_change.py` (new), against a counting repository. This is a class in `tests/fakes.py` that wraps an `InMemoryTodoRepository`, satisfies `TodoRepository` structurally and counts its `update` calls. The existing API tests of S0003 (criteria 10–14 there) must keep passing unchanged and hold the HTTP side.

## Acceptance criteria

1. `change(id, title=" New title ", done=True)` on an open todo returns it titled `New title` and done, with the same id and `created_at`. `get` returns the same afterwards, and the repository saw exactly one `update` call.
2. `change` with one field set, as rows of one parametrized test (`title=" New title "`, `done=True`, `done=False` on a done todo), returns the todo with that change only, after exactly one `update` call.
3. `change(id)` with neither field returns the stored todo unchanged and makes no `update` call.
4. `change(id, title="   ", done=True)` raises `InvalidTitle` with `title must not be blank`. It makes no `update` call, and `get` shows the old title and the todo still open.
5. `change` with an unknown id raises `TodoNotFound` carrying that id and makes no `update` call. There are two rows, with a title and with `done`.
6. `PATCH /todos/{id}` with `{"title": " New title ", "done": true}`, through `create_app` on a service over the counting repository, returns 200 and the todo titled `New title` and done; the repository saw exactly one `update` call.
7. `make check` stays green.
8. docs: `docs/api.md`, *PATCH rules*: the paragraph on two writes is replaced by one sentence: a `PATCH` is one write, so it applies all its changes or none. `docs/project-guide.md`, *Service*: a row for `change`.

## Smoke test

```bash
uv run python -c "
from uuid import uuid4
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService
svc = TodoService(InMemoryTodoRepository())
t = svc.create('Buy milk')
c = svc.change(t.id, title=' Buy oat milk ', done=True)
print(c.title, c.done, c.id == t.id)
try:
    svc.change(t.id, title='   ', done=False)
except Exception as e:
    print(type(e).__name__, '-', e)
print(svc.get(t.id).title, svc.get(t.id).done)
"
```

Expect: three lines, `Buy oat milk True True`, then `InvalidTitle - title must not be blank`, then `Buy oat milk True`.

## Journal
