---
stage: smoke-test
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 3
comments_read: [6267831077]
handed_over: null
claim: null
journal:
- number: 1
  speaker: human
  kind: created
  at: '2026-10-19T12:59:41.186332Z'
  stage: intake
- number: 2
  speaker: factory
  kind: started
  at: '2026-10-19T12:59:41.193394Z'
  stage: intake
- number: 3
  speaker: intake
  kind: question
  at: '2026-10-19T13:00:19.998564Z'
  stage: intake
  run: f831c085e6a34ab980e3c780876fcaf0
  blocked: question
- number: 4
  speaker: human
  kind: comment
  at: '2026-10-19T13:02:40.644386Z'
  stage: intake
- number: 5
  speaker: factory
  kind: started
  at: '2026-10-19T13:02:58.046467Z'
  stage: intake
- number: 6
  speaker: intake
  kind: result
  at: '2026-10-19T13:03:18.813385Z'
  stage: intake
  run: 16fd4f3640864aeb846e2def3e583c46
- number: 7
  speaker: factory
  kind: started
  at: '2026-10-19T13:03:39.084724Z'
  stage: tests
- number: 8
  speaker: tester
  kind: result
  at: '2026-10-19T13:05:53.538531Z'
  stage: tests
  run: 3599e41db6d449e090c4ab04c5d67d78
- number: 9
  speaker: factory
  kind: started
  at: '2026-10-19T13:06:13.686796Z'
  stage: doing
- number: 10
  speaker: coder
  kind: result
  at: '2026-10-19T13:07:49.930733Z'
  stage: doing
  run: d297557698c74b08a0afb35de364b79f
- number: 11
  speaker: factory
  kind: started
  at: '2026-10-19T13:08:10.152509Z'
  stage: review
- number: 12
  speaker: reviewer
  kind: result
  at: '2026-10-19T13:08:44.197239Z'
  stage: review
  run: 89a291fbaa80458aa14ccd8defaf2f98
- number: 13
  speaker: factory
  kind: started
  at: '2026-10-19T13:09:04.337954Z'
  stage: docs
- number: 14
  speaker: documenter
  kind: result
  at: '2026-10-19T13:10:07.116116Z'
  stage: docs
  run: b5f1168aeca94f358d8be1378edb5678
---

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
3. The length rule on both sides, as rows of one parametrized test: `POST /todos` with a 200-character title returns 201; with a 201-character title it returns 422 and the body `{"detail": "title must be at most 200 characters"}`; with a title of 200 characters and surrounding spaces it returns 201.
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
24. `POST /todos` with `{"title": "  Buy milk "}` returns 201 and the title `Buy milk`.
25. `make check` stays green.
26. docs: `docs/api.md` describes each endpoint (method, path, body, success and error statuses), the title rules, the error body `{"detail": "…"}` and the `PATCH` rules, with a curl example for creating and for listing; the README's *Getting started* shows how to start the server and names `/docs` for the interactive schema, and its *Where to look next* links `docs/api.md`.

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

1. 2026-10-19 human: created.
2. factory: started intake as opencode-demo.
3. intake: Intake stopped with one question; everything else checked out.

   1. The Interface says the domain's title rule applies "after stripping", and the schemas put no length or blank rule on `title`. On `POST /todos` that has no criterion for the passing side.
      - The padded title `"  Buy milk "` appears only in the smoke test. Criterion 1 uses an unpadded title.
      - Criterion 3 tests 200 and 201 characters, but not a 200-character title padded with whitespace.
      - A coder who puts `max_length=200` or `strip_whitespace` on `TodoCreate.title` would pass every criterion. Criterion 3 would also pass if the schema checked the length before stripping.
      - Criterion 11 covers stripping for `PATCH` only.

      Options:
      - (a) Add a criterion before the two closing ones: `POST /todos` with `{"title": "  Buy milk "}` returns 201 and the title `Buy milk`.
      - (b) Add a row to criterion 3's parametrized test: a title of 200 characters plus surrounding spaces returns 201.
      - (c) Do both.

      I would choose (c).

   Checks that passed:
   - Interface: concrete modules and signatures. `make openapi` exists in the Makefile, and `docs/openapi.json` is in the coder's write paths.
   - Criteria: each is testable by one test function. The rules with a failing side are covered:
     - blank title: criterion 2.
     - 201-character title: criterion 3.
     - missing field: criterion 4.
     - bad `done` query value: criterion 7.
     - bad id: criterion 9.
     - empty or null `PATCH` body: criterion 12.
     - `PATCH` with an invalid title changing nothing: criterion 13.
     - unknown id: criterion 16.
     - `PATCH` order (title first, then done): criteria 13 and 14.
   - Smoke test: runnable, port 8765. Its `Expect:` line gives five checkable lines that match the five commands that print.
   - Architecture: layers are respected. Only `main` wires the repository, and criterion 23 tests that. The errors map in one place, and the boundaries are Pydantic models.
   - Scope: inside the feature's scope (HTTP API, one error shape, committed OpenAPI) and not in its "Out of scope".
4. 2026-10-19 human: (c), both. Add the criterion before the two closing ones: `POST /todos` with `{"title": "  Buy milk "}` returns 201 and the title `Buy milk`. And add the row to criterion 3's parametrized test: a title of 200 characters with surrounding spaces returns 201. The title is stripped first, then the domain's length and blank rules apply; the schema puts no length or blank rule of its own on `title`.
5. factory: started intake as opencode-demo.
6. intake: accepted. The human's answer (journal entry 4, option (c)) is written into the story. Nothing else is changed.
   - Criterion 3 gets a row: a title of 200 characters with surrounding spaces returns 201.
   - A new criterion 24 is added before the two closing ones: `POST /todos` with `{"title": "  Buy milk "}` returns 201 and the title `Buy milk`. `make check` is now criterion 25 and `docs:` is 26. Criteria 21–23 keep their numbers, so the Interface's references to them still hold.
   - The Description is unchanged. It already says the schema puts no rule on `title`. The feature's decision 18 states the same.

   Checks, re-run with the answer in:
   - Interface: it names concrete modules and signatures (`schemas.py`, `dependencies.py`, `errors.py`, `routes.py`, `app.py`, `main.py`). It matches the existing `TodoService` methods (`create`, `get`, `list(done=)`, `rename`, `complete`, `reopen`, `delete`). `make openapi` exists in the Makefile, and `docs/openapi.json` is in the coder's write paths.
   - Criteria: each is testable by one test function.
     - Every behaviour the Interface states has a criterion, and every rule has one for its failing side.
     - Title stripping on POST: criterion 24, plus the padded row of criterion 3.
     - Title stripping on PATCH: criterion 11.
     - Blank title: criteria 2 and 13.
     - Length limit on both sides: criterion 3.
     - Missing field: criterion 4.
     - Bad `done` query value: criterion 7.
     - Bad id: criterion 9.
     - Unknown id: criterion 16.
     - Empty or null PATCH body: criterion 12.
     - PATCH order, with an invalid title changing nothing: criteria 13 and 14.
     - Error body shape: criterion 20.
     - Service wiring: criteria 17 and 19.
     - App title: criterion 18.
     - OpenAPI file and paths: criteria 21 and 22.
     - Import rule: criterion 23.
   - Smoke test: the commands are runnable (uvicorn on port 8765 with a cleanup trap). The `Expect:` line gives five checkable lines that match the five commands that print.
   - Architecture: it matches `CLAUDE.md`. Only `app.api.main` wires the repository, and criterion 23 tests that. Errors map in one place. Boundaries are Pydantic models, and `get_service` lives in `dependencies.py`.
   - Scope: inside the feature's scope (HTTP API, one error shape, committed OpenAPI schema). It touches nothing in the "Out of scope" list, and it adds no operations endpoints.
7. factory: started tests as opencode-demo.
8. tester: I wrote tests for criteria 1–24 through FastAPI's `TestClient` against `create_app(TodoService(InMemoryTodoRepository(), clock=TickingClock()))`, built from fixtures. The ticking clock makes creation order deterministic. Criteria 25 (`make check` green) and 26 (docs) are not the tests stage's to test.

   Criterion → test:
   - criterion 1: tests/api/test_todos.py::test_create_returns_the_new_open_todo
   - criterion 2: tests/api/test_todos.py::test_create_with_a_blank_title_is_rejected
   - criterion 3: tests/api/test_todos.py::test_create_applies_the_title_length_limit (rows: 200 chars, 201 chars, 200 chars with surrounding spaces)
   - criterion 4: tests/api/test_todos.py::test_create_without_a_title_names_the_missing_field
   - criterion 5: tests/api/test_todos.py::test_list_returns_every_todo_in_creation_order
   - criterion 6: tests/api/test_todos.py::test_list_filters_by_the_done_flag (rows: true, false)
   - criterion 7: tests/api/test_todos.py::test_list_with_an_invalid_done_filter_is_rejected
   - criterion 8: tests/api/test_todos.py::test_get_returns_the_todo
   - criterion 9: tests/api/test_todos.py::test_an_id_that_is_no_uuid_is_rejected (rows: get, patch, delete)
   - criterion 10: tests/api/test_todos.py::test_patch_done_completes_and_reopens_the_todo
   - criterion 11: tests/api/test_todos.py::test_patch_title_renames_the_todo_and_keeps_the_rest
   - criterion 12: tests/api/test_todos.py::test_patch_that_sets_nothing_is_rejected_and_changes_nothing (four rows)
   - criterion 13: tests/api/test_todos.py::test_patch_with_a_blank_title_changes_nothing
   - criterion 14: tests/api/test_todos.py::test_patch_title_and_done_applies_both
   - criterion 15: tests/api/test_todos.py::test_delete_removes_the_todo
   - criterion 16: tests/api/test_todos.py::test_an_unknown_id_is_not_found (rows: get, patch, delete)
   - criterion 17: tests/api/test_todos.py::test_routes_use_the_service_given_to_create_app
   - criterion 18: tests/api/test_todos.py::test_the_api_is_called_todo_service
   - criterion 19: tests/api/test_todos.py::test_each_app_uses_its_own_service
   - criterion 20: tests/api/test_todos.py::test_every_error_body_has_only_a_detail (one row each for the requests of criteria 2, 4, 7, 9 and 16)
   - criterion 21: tests/api/test_openapi.py::test_committed_schema_matches_the_app
   - criterion 22: tests/api/test_openapi.py::test_schema_names_the_todo_paths_with_the_todos_tag
   - criterion 23: tests/api/test_imports.py::test_only_main_imports_the_repository_layer (names only the forbidden import, `app.repository`, for every `app.api` module except `main.py`)
   - criterion 24: tests/api/test_todos.py::test_create_strips_the_title

   Files created: tests/api/__init__.py, tests/api/test_todos.py, tests/api/test_openapi.py, tests/api/test_imports.py, tests/fakes.py, tests/imports.py.

   Shared helpers moved under the standing leave in `CLAUDE.md` (tests keep their names and check the same things):
   - tests/service/test_todo_service.py: `T0` and `TickingClock` moved to tests/fakes.py, so the API tests reuse them instead of copying them.
   - tests/domain/test_imports.py: `_imported_modules` became `imported_modules` in tests/imports.py. It now works out the package from the path relative to `src/app` rather than the domain folder, so the API import test uses it too. The domain results are unchanged.

   `make test` (one run): 1 failed, 78 passed, 2 errors. Modules the test runner could not import: `app.api.app` (tests/api/test_todos.py) and `app.api.main` (tests/api/test_openapi.py). test_imports fails because there are no modules under `src/app/api` yet. All earlier tests still pass after the moves. `make lint` is green.

   Open: nothing.

   `lint`: lint: green (0.0 s)
   `test`: 1 failed, 78 passed, 20 warnings, 2 errors in 2.65s
9. factory: started doing as opencode-demo.
10. coder: Built the HTTP API in `src/app/api/`. All the tests pass without changes, and `make check` is green.
    - `__init__.py`: the package.
    - `schemas.py`:
      - `TodoCreate`, `TodoUpdate` and `TodoRead` with `from_domain`.
      - Neither `TodoCreate` nor `TodoUpdate` has a length or blank rule on `title`; the domain strips the title and applies its rule.
      - `TodoUpdate` has an after-validator that refuses a body setting neither field, so FastAPI answers 422.
    - `dependencies.py`: `get_service` reads the service from `request.app.state`; `Service` is the annotated dependency.
    - `errors.py`: the one place where errors become status codes.
      - `register_error_handlers` maps `TodoNotFound` to 404 and `InvalidTitle` to 422 through a table of error type → status.
      - It turns `RequestValidationError` into one sentence: `"<location joined with dots>: <msg>"` of the first error.
    - `routes.py`:
      - The router with the five endpoints.
      - `PATCH` renames first when a title is given, otherwise it reads the todo. Then it completes or reopens when `done` is given, so an invalid title changes nothing.
      - `DELETE` returns 204 with an empty body.
    - `app.py`: `create_app`, titled "Todo service". It stores the service on `app.state`, includes the router and registers the handlers.
    - `main.py`: the composition root and the only module that imports `app.repository`.
    - `docs/openapi.json`: generated with `make openapi`.

    Main decision: the error handlers are plain typed functions, registered through `app.exception_handler(type)(handler)`. I rejected `app.add_exception_handler` with handlers that take `Exception`: Starlette's typing would then need an `isinstance` assert or a `cast` inside each handler, and ruff refuses the assert (S101).

    Refactor: I made one change. `PATCH` first read the todo even when a rename would return it; now it reads only when no title is given. Behaviour is the same and `make check` is green afterwards.

    Noticed but did not touch:
    - `DuplicateTodo` has no status mapping, because the Interface's table leaves it out. It cannot come from the API anyway, since ids are generated server-side.
    - A `PATCH` that sets both fields does two writes (rename, then complete or reopen). That is fine in memory; whether a later repository needs both writes to succeed or fail together is open.
    - FastAPI's test client prints a StarletteDeprecationWarning (httpx → httpx2) during `make test`. That is a dependency matter, outside this story.

    The journal did not change the meaning of the task beyond what intake already wrote into the Description and criteria.

    `check`: check: green
    `duplicates`: duplicates: 0 similar code, 6 dead code, in .reports/
11. factory: started review as opencode-demo.
12. reviewer: no findings

    I read the story and the diff `git diff main...HEAD -- . ':!factory'`. I did not open `docs/openapi.json` by hand, because criterion 21's test checks that it is current.

    What I checked:
    - **Acceptance criteria:**
      - Each of criteria 1–24 has a test in `tests/api/test_todos.py`, `tests/api/test_openapi.py` or `tests/api/test_imports.py`. Each test checks the criterion it is named after.
      - The title length limit is tested on both sides as rows of one parametrized test: 200 characters, 201 characters, and 200 characters with surrounding spaces.
      - Every failing side the Interface states has a test:
        - blank title (criteria 2 and 13)
        - missing field (4)
        - bad `done` query value (7)
        - id that is not a UUID (9)
        - `PATCH` body that sets nothing, or only `null`s (12)
        - unknown id (16)
      - The coder's entry 10 records `check: green`.
    - **Architecture:**
      - Only `app.api.main` imports `app.repository`.
      - `routes.py` takes the service through `Service`, and `get_service` reads it from `app.state`.
      - Errors become status codes in one place, `errors.py`, through one table.
      - The edge uses Pydantic schemas, and the API imports only the service and the domain.
    - **Security:** I saw no secrets and no marker that silences a check. Error bodies carry only the domain's message or the first validation error's location and message.
    - **Quality:**
      - Names are clear, and each function does one thing.
      - Comments explain why: in `routes.py` (rename first) and in `errors.py` (one sentence instead of FastAPI's list).
      - `app.api` modules carry module docstrings, which is all `CLAUDE.md` asks of that layer.
      - The shared helpers `tests/fakes.py` and `tests/imports.py` are moves, not second copies.
    - **Work item hygiene:**
      - The journal gives the main decision (typed handlers registered with `app.exception_handler`) and what was rejected (`add_exception_handler` with `Exception` handlers).
      - The Description matches what was built.
      - The docs criterion, 26, still says what the reader needs to know.

    Earlier tests:
    - `tests/service/test_todo_service.py`: standing leave to move a shared test helper. `T0` and `TickingClock` moved to `tests/fakes.py`, and every test keeps its name and what it checks.
    - `tests/domain/test_imports.py`: standing leave to move a shared test helper. `_imported_modules` moved to `tests/imports.py` as `imported_modules`, which now works out the package from `src/app`. For domain files it gives the same package as before, and the test keeps its name and what it checks.
13. factory: started docs as opencode-demo.
14. documenter: Wrote the documentation for criterion 26 and cross-read the rest. No findings: the code matches the Interface and the criteria.

    Files changed:
    - `docs/api.md` (new):
      - Covers how to run the server and each endpoint (method, path, body, success and error statuses).
      - Covers the `done` filter, the title rules (strip first, blank, 200/201 limit), the `PATCH` rules, and the one error body `{"detail": "..."}` with the status mapping.
      - Has curl examples for create and list, plus complete and delete.
      - Notes that a `PATCH` setting both fields is two repository writes, taken from the coder's open point.
    - `README.md`:
      - *Getting started* now shows how to start the server and names `/docs` for the interactive schema, with a curl create and list.
      - *Where to look next* links `docs/api.md` and mentions the API modules in the project-guide line.
    - `docs/project-guide.md`:
      - "Built so far" now includes the HTTP API.
      - A new *API* section lists the `app.api` modules, how the service is wired per app, and where to add an error mapping.
      - It records that `DuplicateTodo` has no mapping because ids are generated server-side.

    Cross-read and found current:
    - `docs/project-guide.md`: the layers table, which already listed `app.api` and `app.api.main` as the wiring place; the domain, errors, repository and service sections; the Try it examples.
    - `CLAUDE.md`'s Docs section: it names `docs/api.md` and `docs/decisions.md`.
    - `docs/openapi.json`: generated, not read or edited; criterion 21's test keeps it current.

    Seen but not touched:
    - The README intro says todos are "kept in memory or in a SQLite file". SQLite arrives in a later story, so today only memory is true. I left the sentence because the intro says the README grows with the build. The SQLite story's docs should settle it.
    - `docs/decisions.md` does not exist yet, though `CLAUDE.md` names it. The coder's main decision (typed handlers registered with `app.exception_handler`) is in the journal only; the human decides whether it belongs in a decision log.
    - The detail text after the location prefix (for example `Input should be a valid UUID, ...`) is Pydantic's wording. `docs/api.md` says only the prefix (`body`, `query`, `path`) is stable.

    `check`: check: green
