---
stage: intake
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: null
comments_read: []
handed_over: null
claim:
  instance: opencode-demo
  stage: intake
  started_at: '2026-10-19T13:30:29.871178Z'
  lease_duration: 60
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
