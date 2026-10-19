---
stage: tests
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 8
comments_read: []
handed_over: null
claim:
  instance: opencode-demo
  stage: tests
  started_at: '2026-10-19T13:50:42.490706Z'
  lease_duration: 60
journal:
- number: 1
  speaker: human
  kind: created
  at: '2026-10-19T13:49:56.258485Z'
  stage: intake
- number: 2
  speaker: factory
  kind: started
  at: '2026-10-19T13:49:56.262090Z'
  stage: intake
- number: 3
  speaker: intake
  kind: result
  at: '2026-10-19T13:50:22.347228Z'
  stage: intake
  run: c50385aa2d164979a155c425f078191c
- number: 4
  speaker: factory
  kind: started
  at: '2026-10-19T13:50:42.490706Z'
  stage: tests
---

# Todo statistics

## Description

Count the todos for a glance at the data: how many are open, how many done, and the total. The service computes the counts from what the repository lists; the API exposes them as `GET /stats`. No new repository method, no domain change.

## Interface

`src/app/service/todo_service.py`

```python
@dataclass(frozen=True, slots=True)
class TodoStats:
    open: int
    done: int

    @property
    def total(self) -> int: ...

class TodoService:
    def stats(self) -> TodoStats: ...
```

- `total` is `open + done`, derived, not a field.
- `stats` counts over the repository's list in one pass; the existing methods keep their behaviour.

`src/app/api/schemas.py`

```python
class StatsRead(BaseModel):
    open: int
    done: int
    total: int

    @classmethod
    def from_stats(cls, stats: TodoStats) -> "StatsRead": ...
```

`src/app/api/stats.py`

```python
router = APIRouter(tags=["stats"])

@router.get("/stats")
def read_stats(service: Service) -> StatsRead: ...
```

`create_app` includes the stats router beside the others.

Tests: `tests/service/test_stats.py` (with a repository that counts its calls, a fake of `TodoRepository` in that module around `InMemoryTodoRepository`) and `tests/api/test_stats.py`.

## Acceptance criteria

1. `stats()` on an empty repository returns `TodoStats(open=0, done=0)`, whose `total` is 0.
2. With two open todos and one completed, `stats()` returns `open == 2`, `done == 1` and `total == 3`.
3. `TodoStats` is frozen: assigning to `open` raises `dataclasses.FrozenInstanceError` (`setattr` with the field's name in a variable).
4. `total` is not a dataclass field: `dataclasses.fields(TodoStats)` names exactly `open` and `done`.
5. `stats()` reads the repository once: with a repository that counts its calls, one `stats()` call makes exactly one `list_all` call and no other call.
6. `GET /stats` returns 200 and exactly the counts, as rows of one parametrized test: `{"open": 2, "done": 1, "total": 3}` on the data of criterion 2, and `{"open": 0, "done": 0, "total": 0}` on an empty repository.
7. `/stats` is in `app.openapi()["paths"]` with the tag `stats`, and `/todos`, `/todos/{todo_id}` and `/health` are still there.
8. `docs/openapi.json` still equals `app.openapi()` of `app.api.main.app` (the existing test of F0001-S0003; the coder runs `make openapi`).
9. `make check` stays green.
10. docs: `docs/api.md` describes `GET /stats` and its three fields in the endpoint table, with one curl example.

## Smoke test

```bash
uv run python -c "
from fastapi.testclient import TestClient
from app.api.main import build_app
c = TestClient(build_app({}))
for t in ('Buy milk', 'Write the docs', 'Call mum'):
    c.post('/todos', json={'title': t})
first = c.get('/todos').json()[0]['id']
c.patch(f'/todos/{first}', json={'done': True})
print(c.get('/stats').json())
"
```

Expect: one line, `{'open': 2, 'done': 1, 'total': 3}`.

## Journal

1. 2026-10-19 human: created.
2. factory: started intake as opencode-demo.
3. intake: accepted
   - Interface: concrete modules and signatures (`TodoStats`, `TodoService.stats`, `StatsRead.from_stats`, `app/api/stats.py` router). They fit the existing code (`Service` dependency, health router pattern, `create_app` including routers). The stated behaviours (`total` derived, one pass, existing methods unchanged) are covered by criteria 4 and 5 and the existing tests.
   - Criteria: each is testable by one test function without further decisions. Empty and mixed counts are criteria 1 and 2, frozen is 3, `total` not a field is 4, one `list_all` call and no other is 5, the endpoint on both data sets is 6, the route and tag with the other routes still present is 7, and the openapi file is 8. The Interface states no limit, validation or error, so no rule lacks its failing side.
   - Smoke test: runnable. `build_app({})` selects the in-memory repository, and POST `/todos` and PATCH `/todos/{id}` with `done` exist. The Expect line is one exact output line and does not depend on which todo is completed.
   - Architecture: the stats logic stays in `app.service` and uses the repository protocol's `list_all` only. The API imports the service type (api → service, allowed), and domain and repository are untouched. The router uses `Service` from `dependencies.py` and is included in `create_app`, so wiring stays in `app.api.main`.
   - Scope: within `feature.md` (`GET /stats: open, done, total`; decisions 3 and 9) and outside its "Out of scope". No test of another story is changed.
4. factory: started tests as opencode-demo.
