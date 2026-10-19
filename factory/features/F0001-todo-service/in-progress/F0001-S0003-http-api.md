# HTTP API

## Description

Expose the service over HTTP with FastAPI: create, list (optionally filtered by `done`), read, update and delete todos as JSON. Pydantic schemas at the edge, one error shape for every error (`{"detail": "<one sentence>"}`), errors mapped to status codes in one place, and the concrete repository chosen only in the composition root, still in memory. The OpenAPI schema is committed as `docs/openapi.json`, which the coder writes with `make openapi` (the one file under `docs/` in the coder's write paths). Single user, no authentication.

## Interface

`src/app/api/schemas.py`

```python
class TodoCreate(BaseModel):
    title: str

class TodoUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None

class TodoRead(BaseModel):
    id: UUID
    title: str
    done: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, todo: Todo) -> "TodoRead": ...
```

The schemas put no length or blank rule on `title`: the domain's rule applies, after stripping, with the domain's message. A `TodoUpdate` that sets neither field (both absent or `null`) is rejected with 422. A field sent as `null` counts as not set.

`src/app/api/dependencies.py`

```python
def get_service(request: Request) -> TodoService: ...
Service = Annotated[TodoService, Depends(get_service)]
```

`get_service` returns the service `create_app` was given; every router takes the service through `Service`.

`src/app/api/errors.py`

```python
def register_error_handlers(app: FastAPI) -> None: ...
```

| Raised | Status | Body |
| :- | -: | :- |
| `TodoNotFound` | 404 | `{"detail": "todo <id> not found"}` (the error's message) |
| `InvalidTitle` | 422 | `{"detail": "<the error's message>"}` |
| `RequestValidationError` | 422 | `{"detail": "<location>: <message>"}` of the first error, the location joined with dots, e.g. `body.title: Field required` |

`src/app/api/routes.py`: `router = APIRouter(prefix="/todos", tags=["todos"])`

| Method | Path | Body | Success | Errors |
| :- | :- | :- | :- | :- |
| POST | `/todos` | `TodoCreate` | 201, `TodoRead` | 422 |
| GET | `/todos`, optional query `done=true\|false` | | 200, `list[TodoRead]` in creation order | 422 |
| GET | `/todos/{todo_id}` | | 200, `TodoRead` | 404, 422 |
| PATCH | `/todos/{todo_id}` | `TodoUpdate` | 200, `TodoRead` | 404, 422 |
| DELETE | `/todos/{todo_id}` | | 204, empty body | 404, 422 |

`PATCH` applies `title` first (rename), then `done` (`true` completes, `false` reopens), so an invalid title changes nothing.

`src/app/api/app.py`

```python
def create_app(service: TodoService) -> FastAPI: ...   # titled "Todo service"; stores the service, includes the router, registers the handlers
```

`src/app/api/main.py`

```python
app = create_app(TodoService(InMemoryTodoRepository()))   # the only module that imports app.repository
```

Run with `uv run uvicorn app.api.main:app --port 8765`. `make openapi` writes `docs/openapi.json` from `app.api.main:app`; the coder runs it after the routes exist.

Tests: `tests/api/test_todos.py` through FastAPI's `TestClient` against `create_app(TodoService(InMemoryTodoRepository()))` from a fixture; `tests/api/test_openapi.py` (criteria 21 and 22); `tests/api/test_imports.py` (criterion 23, naming only the forbidden import).

## Acceptance criteria

1. `POST /todos` with `{"title": "Buy milk"}` returns 201 and a body with exactly the keys `id`, `title`, `done`, `created_at`: a UUID, `"Buy milk"`, `false`, and an ISO 8601 timestamp whose offset is UTC (`Z` or `+00:00`).
2. `POST /todos` with `{"title": "   "}` returns 422 and the body `{"detail": "title must not be blank"}`.
3. The length rule on both sides, as rows of one parametrized test: `POST /todos` with a 200-character title returns 201; with a 201-character title it returns 422 and the body `{"detail": "title must be at most 200 characters"}`.
4. `POST /todos` with `{}` returns 422 and the body `{"detail": "body.title: Field required"}`.
5. `GET /todos` returns 200 and every todo, in creation order.
6. The done filter, as rows of one parametrized test: `GET /todos?done=true` returns only the completed todos, and `GET /todos?done=false` only the open ones.
7. `GET /todos?done=maybe` returns 422 and a body whose only key is `detail`, a string starting with `query.done: `.
8. `GET /todos/{id}` for a known id returns 200 and that todo.
9. `GET`, `PATCH` (with `{"done": true}`) and `DELETE` of `/todos/not-a-uuid` each return 422 and a body whose only key is `detail`, a string starting with `path.todo_id: `: three rows of one parametrized test.
10. `PATCH /todos/{id}` with `{"done": true}` returns 200 and the todo completed; a following `PATCH` with `{"done": false}` returns it open.
11. `PATCH /todos/{id}` with `{"title": " New title "}` returns 200 and the todo titled `New title`, with the same id, done flag and `created_at` as before.
12. `PATCH /todos/{id}` with `{}`, `{"title": null}`, `{"done": null}` and `{"title": null, "done": null}` (four rows of one parametrized test) returns 422 and a body whose only key is `detail`, a string; a `GET` of the todo afterwards shows it as before.
13. `PATCH /todos/{id}` with `{"title": "   ", "done": true}` returns 422 and the body `{"detail": "title must not be blank"}`; a `GET` afterwards shows the old title and the todo still open.
14. `PATCH /todos/{id}` with `{"title": " New title ", "done": true}` on an open todo returns 200 and the todo titled `New title` and completed, with the same id and `created_at`; a `GET` afterwards shows both changes.
15. `DELETE /todos/{id}` returns 204 with an empty body, and a `GET` of that id returns 404 afterwards.
16. `GET`, `PATCH` (with `{"done": true}`) and `DELETE` of `/todos/{id}` for an unknown id each return 404 and the body `{"detail": "todo <id> not found"}`, the id in its hyphenated form: three rows of one parametrized test.
17. The routes use the service given to `create_app`: a todo created directly through that service is returned by `GET /todos`.
18. The API is called `Todo service`: `app.openapi()["info"]["title"]` of `create_app(service)` is `"Todo service"`.
19. `get_service` hands each route the service of its own app: two apps built by `create_app` on two services each list only the todos of their own service.
20. Every error body the API returns has `detail` as its only key: the bodies of criteria 2, 4, 7, 9 and 16 are dicts with exactly the key `detail`, never a list.
21. `docs/openapi.json`, parsed as JSON, equals `app.openapi()` of `app.api.main.app`.
22. The schema of `app.api.main.app` names the paths `/todos` and `/todos/{todo_id}` with the tag `todos`.
23. Of the `app.api` modules, only `app.api.main` imports `app.repository`.
24. `make check` stays green.
25. docs: `docs/api.md` describes each endpoint (method, path, body, success and error statuses), the title rules, the error body `{"detail": "…"}` and the `PATCH` rules, with a curl example for creating and for listing; the README's *Getting started* shows how to start the server and names `/docs` for the interactive schema, and its *Where to look next* links `docs/api.md`.

## Smoke test

```bash
d=$(mktemp -d); trap 'kill $pid 2>/dev/null; wait $pid 2>/dev/null; rm -rf "$d"' EXIT
uv run uvicorn app.api.main:app --port 8765 >"$d/uvicorn.log" 2>&1 & pid=$!
for i in $(seq 40); do curl -s -o /dev/null localhost:8765/todos && break; sleep 0.5; done
ID=$(curl -s -X POST localhost:8765/todos -H 'content-type: application/json' -d '{"title":"  Buy milk "}' | uv run python -c "import json, sys; print(json.load(sys.stdin)['id'])")
curl -s -X PATCH localhost:8765/todos/$ID -H 'content-type: application/json' -d '{"done":true}'; echo
curl -s 'localhost:8765/todos?done=false'; echo
curl -s -X POST localhost:8765/todos -H 'content-type: application/json' -d '{"title":"   "}'; echo
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:8765/todos/$ID
curl -s localhost:8765/todos/$ID; echo
```

Expect: five lines: the todo as JSON with `"title":"Buy milk"` and `"done":true`; then `[]`; then `{"detail":"title must not be blank"}`; then `204`; then `{"detail":"todo <the same id> not found"}`.

## Journal
