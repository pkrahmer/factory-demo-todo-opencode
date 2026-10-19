---
stage: approval
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 6
comments_read: []
handed_over: approval
claim: null
journal:
- number: 1
  speaker: human
  kind: created
  at: '2026-10-19T13:30:29.864059Z'
  stage: intake
- number: 2
  speaker: factory
  kind: started
  at: '2026-10-19T13:30:29.871178Z'
  stage: intake
- number: 3
  speaker: intake
  kind: result
  at: '2026-10-19T13:30:55.045991Z'
  stage: intake
  run: a14eb8c6760d40aca044472b95c164b0
- number: 4
  speaker: factory
  kind: started
  at: '2026-10-19T13:31:16.163079Z'
  stage: tests
- number: 5
  speaker: tester
  kind: result
  at: '2026-10-19T13:32:09.035758Z'
  stage: tests
  run: f07992d8a1b64bc0941a99afab3c6740
- number: 6
  speaker: factory
  kind: started
  at: '2026-10-19T13:32:30.433763Z'
  stage: doing
- number: 7
  speaker: coder
  kind: result
  at: '2026-10-19T13:33:26.308834Z'
  stage: doing
  run: 2321212d028447a29ae43ebd48cbeccb
- number: 8
  speaker: factory
  kind: started
  at: '2026-10-19T13:33:47.251713Z'
  stage: review
- number: 9
  speaker: reviewer
  kind: result
  at: '2026-10-19T13:34:17.395260Z'
  stage: review
  run: 799b970a22b4498c981dd75653f14cc3
- number: 10
  speaker: factory
  kind: started
  at: '2026-10-19T13:34:37.960960Z'
  stage: docs
- number: 11
  speaker: documenter
  kind: result
  at: '2026-10-19T13:35:27.205310Z'
  stage: docs
  run: 5905ceb6232b4700adbc593d0e3532f0
- number: 12
  speaker: factory
  kind: started
  at: '2026-10-19T13:35:47.343301Z'
  stage: smoke-test
- number: 13
  speaker: smoke-tester
  kind: result
  at: '2026-10-19T13:36:12.538685Z'
  stage: smoke-test
  run: 8944aea089a147bca2ba6fdd196048d9
---

# Health endpoint

## Description

Give a monitor something to poll: `GET /health` answers 200 with the status, the package version and which storage the running app uses, without touching the repository, so it answers even when the database does not. The composition root gains `build_app`, which builds the whole app from the environment and tells `create_app` the storage kind.

## Interface

`src/app/api/schemas.py`

```python
class HealthRead(BaseModel):
    status: Literal["ok"]
    version: str
    storage: Literal["memory", "sqlite"]
```

`src/app/api/health.py`

```python
router = APIRouter(tags=["health"])

@router.get("/health")
def read_health(request: Request) -> HealthRead: ...
```

`src/app/api/app.py`

```python
def create_app(service: TodoService, *, storage: Literal["memory", "sqlite"] = "memory") -> FastAPI: ...
```

`src/app/api/main.py`

```python
def build_app(environ: Mapping[str, str]) -> FastAPI: ...
app = build_app(os.environ)
```

- `version` is `importlib.metadata.version("app")`.
- `create_app` stores the storage kind and includes the health router beside the todo router; existing callers that pass only the service get `"memory"`.
- `build_app` passes `"sqlite"` when `build_repository` chose SQLite (`TODO_DB` set and not empty), else `"memory"`.

Tests: `tests/api/test_health.py` through `TestClient`; the repository that raises on every method is a fake of `TodoRepository` in that module.

## Acceptance criteria

1. `GET /health` on `create_app(service)` returns 200 and exactly the body `{"status": "ok", "version": <importlib.metadata.version("app")>, "storage": "memory"}`.
2. `GET /health` on `create_app(service, storage="sqlite")` reports `"storage": "sqlite"`.
3. `build_app` reports the storage the environment chose, as rows of one parametrized test: `build_app({})` and `build_app({"TODO_DB": ""})` answer `/health` with `"storage": "memory"`, and `build_app({"TODO_DB": <a path under tmp_path>})` with `"storage": "sqlite"`.
4. `/health` does not use the repository: with a service whose repository raises on every method, it still returns 200.
5. `build_app` hands the todo routes the repository the environment chose, as rows of one parametrized test: a todo `POST`ed through `build_app({"TODO_DB": p})` (`p` under `tmp_path`) is listed by `GET /todos` of a second `build_app({"TODO_DB": p})`; a todo `POST`ed through `build_app({})` is listed by the same app and not by a second `build_app({})`.
6. `/health` is in `app.openapi()["paths"]` with the tag `health`, and `/todos` and `/todos/{todo_id}` are still there.
7. `docs/openapi.json` still equals `app.openapi()` of `app.api.main.app` (the existing test of F0001-S0003; the coder runs `make openapi`).
8. `make check` stays green.
9. docs: `docs/api.md` describes `/health` (the three fields and that it never touches storage); the README mentions it as the way to check a running server.

## Smoke test

```bash
uv run python -c "
from fastapi.testclient import TestClient
from app.api.main import build_app
print(TestClient(build_app({})).get('/health').json())
"
```

Expect: one line, `{'status': 'ok', 'version': '0.1.0', 'storage': 'memory'}`.

## Journal

1. 2026-10-19 human: created.
2. factory: started intake as opencode-demo.
3. intake: accepted

   - Interface: Concrete. It names the modules and signatures: `HealthRead` in `api/schemas.py`, `router` and `read_health` in the new `api/health.py`, `create_app(service, *, storage=...)` in `api/app.py`, and `build_app(environ)` plus `app = build_app(os.environ)` in `api/main.py`. The current `main.py` and `app.py` match the starting point the story describes. `build_repository` stays, so the existing tests in `tests/api/test_main.py` are unaffected and the story names no other story's test to change. The Interface also states `version` is `importlib.metadata.version("app")`; `pyproject.toml` has `name = "app"`, `version = "0.1.0"`.
   - Criteria: Each one can be tested by a single test function, and the parametrized ones are laid out as rows.
     - Criterion 1 covers the default `"memory"`, the exact body and the metadata version.
     - Criterion 2 covers `storage="sqlite"`.
     - Criterion 3 covers all three `build_app` rows: missing `TODO_DB`, empty `TODO_DB`, and a set path.
     - Criterion 4 covers a repository that raises on every method.
     - Criterion 5 covers the todo routes on both sides: the persistent repository is shared by a second app, and the in-memory one is not.
     - Criteria 6 and 7 cover the OpenAPI paths, the `health` tag and the committed schema.
     - Every Interface clause has a criterion: the version source, the `"memory"` default for callers that pass only the service, and `"sqlite"` only when `TODO_DB` is set and non-empty. The empty-string rejection is criterion 3's second row, and no input is refused, so there is no further failing side.
   - Smoke test: Runnable as written, with `uv run python -c` against `build_app({})` through `TestClient`. The `Expect:` line gives one exact output, `{'status': 'ok', 'version': '0.1.0', 'storage': 'memory'}`, which matches the current `pyproject.toml` version.
   - Architecture: Fits the layers. `app.api` holds the router, schema and wiring, and `build_app` sits in the composition root, which is the only place that chooses the concrete repository. `/health` reads the storage kind from app state and never touches the service or repository. `HealthRead` is a Pydantic boundary model. No new dependency.
   - Scope: Inside F0002's scope (`GET /health`: status, version, storage kind). It touches nothing in "Out of scope". Feature decisions 1, 6 and 7 are each covered by a criterion (4, 3, 5).
4. factory: started tests as opencode-demo.
5. tester: Wrote the tests for the health endpoint, one test function per testable criterion, all in `tests/api/test_health.py`, through `TestClient`.

   - criterion 1: tests/api/test_health.py::test_health_reports_ok_version_and_memory_by_default (exact body, version from `importlib.metadata.version("app")`)
   - criterion 2: tests/api/test_health.py::test_health_reports_the_storage_given_to_create_app
   - criterion 3: tests/api/test_health.py::test_build_app_reports_the_storage_the_environment_chose (three rows: missing, empty, set; uses the shared `db_path` fixture)
   - criterion 4: tests/api/test_health.py::test_health_does_not_touch_the_repository (`RaisingRepository` is a structural fake of `TodoRepository` in this module; every method raises)
   - criterion 5: tests/api/test_health.py::test_build_app_hands_the_todo_routes_the_chosen_repository (two rows: sqlite, where a second app sees the todo, and memory, where it does not; the first app lists the todo in both rows)
   - criterion 6: tests/api/test_health.py::test_schema_names_health_with_its_tag_beside_the_todo_paths (on `create_app(service).openapi()`)
   - criterion 7: the existing tests/api/test_openapi.py::test_committed_schema_matches_the_app; no new test, and the coder runs `make openapi`
   - criteria 8 and 9 (`make check`, docs): no test.

   Files created: tests/api/test_health.py. No earlier test file changed.

   `make test`: the run could not import `tests/api/test_health.py`, because `app.api.main` has no `build_app` yet. The test would also fail on the `create_app(..., storage=...)` keyword and on the missing `/health` route. The other 146 tests pass. `make lint` is green.

   `lint`: lint: green (0.0 s)
   `test`: 146 passed, 20 warnings, 1 error in 3.72s
6. factory: started doing as opencode-demo.
7. coder: Built the health endpoint and the `build_app` composition root. `make check` is green: 155 passed, coverage 100%.

   - `src/app/api/health.py` (new): `router` has the tag `health`. `read_health` reads the storage kind from `request.app.state.storage` and the version from `importlib.metadata.version("app")`. It never touches the service or the repository.
   - `src/app/api/schemas.py`: `HealthRead`, plus a type alias `StorageKind = Literal["memory", "sqlite"]`. `HealthRead.storage` and `create_app` both use it, so the two kinds are written in one place.
   - `src/app/api/app.py`: `create_app(service, *, storage="memory")` stores `app.state.storage` and includes the health router beside the todo router.
   - `src/app/api/main.py`: `build_app(environ)` builds the service from `build_repository` and passes the storage kind to `create_app`. `app = build_app(os.environ)`.
   - `docs/openapi.json`: regenerated with `make openapi`.

   Main decision: the rule "`TODO_DB` set and not empty means SQLite" now lives once, in a private `_storage_kind(environ)` in `main.py`. `build_repository` and `build_app` both use it, so the storage a monitor sees and the repository the routes get cannot drift apart. Rejected: deciding the kind in `build_app` with an `isinstance` check on the repository. It would tie the reported kind to concrete class names rather than to the environment rule, and it would add a second branch.

   Refactor pass: I read the diff and found nothing to change.

   Noticed, not touched: the spelled-out Literals in the Interface are replaced by the equivalent alias `StorageKind`. The behaviour and the schema are the same. The docs criterion (`docs/api.md`, README) is left for the documenter.

   `check`: check: green
   `duplicates`: duplicates: 0 similar code, 7 dead code, in .reports/
8. factory: started review as opencode-demo.
9. reviewer: no findings

   I read the work item and `git diff main...HEAD -- . ':!factory'`. I did not read the generated `docs/openapi.json` diff; whether it is current is covered by criterion 7's existing test and the green `make check` in entry 7.

   - **Acceptance criteria:** Criteria 1 to 6 each have a test in `tests/api/test_health.py`, and each test checks what its criterion says.
     - Criterion 1 checks the exact body, with the version taken from `importlib.metadata.version("app")`.
     - Criterion 2 checks that `storage="sqlite"` is reported.
     - Criterion 3 has the three rows: `TODO_DB` missing, empty and set.
     - Criterion 4 uses `RaisingRepository` with `raise_server_exceptions=False`, so any use of the repository would turn the 200 into a 500.
     - Criterion 5 has two rows: SQLite shared with a second app, and memory not shared.
     - Criterion 6 checks the `health` tag and that the `/todos` paths are still there.
     - Criterion 7 is the existing test in `tests/api/test_openapi.py`.
     - The Interface refuses no input, so there is no failing side left untested. The empty `TODO_DB` boundary is criterion 3's second row.
   - **Architecture:** `health.py` reads only `app.state.storage` and never calls the service or the repository. The concrete repository is still chosen only in `app.api.main`. `HealthRead` is a Pydantic model at the boundary. `app.state.storage` is untyped, but it is assigned to a variable typed `StorageKind` and Pydantic validates it straight away in `HealthRead`.
   - **Security:** No markers that silence a check, no secrets, no strings built into shell or SQL.
   - **Quality:** The coder's alias `StorageKind` in `schemas.py` means the same as the Literal spelled out in the Interface, and it keeps the two kinds in one place. The private `_storage_kind` in `main.py` holds the "`TODO_DB` set and not empty means SQLite" rule once, for both `build_repository` and `build_app`. The `service` fixture in `test_health.py` is not a copy: the fixtures in `test_todos.py` and `test_todo_service.py` use other clocks. No existing helper in `tests/fakes.py` or `tests/conftest.py` was copied; the shared `db_path` fixture is reused.
   - **Work item hygiene:** Entry 7 gives the main decision and what was rejected. The Description matches what was built, and the docs criterion still says what a reader needs to know.

   Earlier tests: none. The diff only adds `tests/api/test_health.py` and changes no test file that `main` already holds.
10. factory: started docs as opencode-demo.
11. documenter: Documented `GET /health` and `build_app`.

    Files changed:
    - `docs/api.md`: the *Running it* section now describes `build_app(environ)` and `create_app(service, *, storage="memory")`. A new *Health* section under *Endpoints* gives the three fields, `status`, `version` and `storage`, and where each comes from. It says the handler never touches the service or the repository, so a 200 means the server is running, not that the todos are reachable. It adds a `curl` example.
    - `README.md`: in *Getting started*, `GET /health` is named as the way to check a running server, with the expected body and a `curl` line. The *Where to look next* entry for `docs/api.md` now lists `/health`.
    - `docs/project-guide.md`:
      - *Choosing the repository* now covers `build_app`, the shared private `_storage_kind` rule, and why the reported kind cannot differ from the chosen repository.
      - The API module table adds `health` and `HealthRead` / `StorageKind`, and updates the `app` and `main` rows.
      - A sentence after the table says the storage kind is app state that `build_app` keeps equal to the repository it chose.
      - Step 3 of *Adding a repository* says to give the new repository a `StorageKind` value.

    Cross-read and found current against the diff: the rest of `docs/api.md` (storage, endpoints table, title and PATCH rules, errors, examples) and the rest of `docs/project-guide.md` (layers, domain, repositories, service, *Try it*). I did not read `docs/openapi.json`, since it is generated, and criterion 7's existing test covers it.

    Findings for the coder: none. The code matches the Interface. The one difference is the `StorageKind` alias in place of the spelled-out Literal, which the coder and reviewer already noted. Public docstrings are not required in `app.api`.

    Stale text I noticed but did not touch: none.

    `check`: check: green
12. factory: started smoke-test as opencode-demo.
13. smoke-tester: I ran the one command under `## Smoke test` from the repository root, exactly as written, and fixed nothing.

    Command 1: `uv run python -c "...print(TestClient(build_app({})).get('/health').json())"`

    ```
    /work/checkout/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
      from starlette.testclient import TestClient as TestClient  # noqa
    {'status': 'ok', 'version': '0.1.0', 'storage': 'memory'}
    ```

    Expect: one line, `{'status': 'ok', 'version': '0.1.0', 'storage': 'memory'}`. **Met.**
    - The printed line is exactly the expected one.
    - The first two lines are a warning that an installed package (starlette's test client) prints on stderr. They do not come from this story's code. I ran the command again with stderr thrown away (`2>/dev/null | wc -l`), and stdout is exactly 1 line.
    - I judged the "one line" on stdout, so the warning is not a finding. If the human wants "one line" to cover stderr too, the warning comes from the pinned dependencies, not from this story.

    Against the acceptance criteria, the output contradicts none of them:
    - `status` is `ok` and `version` is `0.1.0`, the version in `pyproject.toml` (criterion 1).
    - `build_app({})` reports `storage: memory` (criteria 1 and 3).
    - The smoke test does not exercise the other criteria (2 and 4 to 9).

    Findings: none.
