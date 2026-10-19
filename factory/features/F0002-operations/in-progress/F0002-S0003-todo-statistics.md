---
stage: doing
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 8
comments_read: []
handed_over: null
claim:
  instance: opencode-demo
  stage: doing
  started_at: '2026-10-19T13:52:06.878891Z'
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
- number: 5
  speaker: tester
  kind: result
  at: '2026-10-19T13:51:46.270472Z'
  stage: tests
  run: dc67d5f03e3d4a8399999685d64e5643
- number: 6
  speaker: factory
  kind: started
  at: '2026-10-19T13:52:06.878891Z'
  stage: doing
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
5. tester: Wrote the tests for the todo statistics, one test per criterion. They are red on purpose and are the coder's specification.

   - criterion 1: tests/service/test_stats.py::test_stats_of_an_empty_repository_are_zero
   - criterion 2: tests/service/test_stats.py::test_stats_count_open_and_done_todos
   - criterion 3: tests/service/test_stats.py::test_stats_are_frozen
   - criterion 4: tests/service/test_stats.py::test_total_is_not_a_dataclass_field
   - criterion 5: tests/service/test_stats.py::test_stats_read_the_repository_with_one_list_all_call (`CountingRepository` in the module wraps `InMemoryTodoRepository` and records every method call. The data is added to the inner repository before wrapping, so only the calls of `stats()` are recorded. The test expects exactly `["list_all"]`.)
   - criterion 6: tests/api/test_stats.py::test_get_stats_returns_the_counts (one parametrized test with two rows: `mixed` and `empty`)
   - criterion 7: tests/api/test_stats.py::test_schema_names_stats_with_its_tag_beside_the_other_paths (uses `app.api.main.app.openapi()`)
   - criterion 8: tests/api/test_openapi.py::test_committed_schema_matches_the_app (existing test, unchanged; the coder runs `make openapi`)
   - criteria 9 and 10: `make check` and the docs; nothing to test.

   Files created: tests/service/test_stats.py, tests/api/test_stats.py.

   Earlier test files changed under the standing leave to move a shared test helper: the `HTTP_METHODS` constant was copied in tests/api/test_health.py and tests/api/test_openapi.py, and the new test needs it too. I moved it to tests/fakes.py and changed both files to import it from there. Every test keeps its name and checks the same thing.

   `make test` result: 3 failed, 165 passed, 1 error. tests/service/test_stats.py cannot be imported because `TodoStats` is not yet in `app.service.todo_service`. The API tests fail because `/stats` returns 404 and is missing from the schema. No other module failed to import. `make lint` is green.

   Nothing is open.

   `lint`: lint: green (0.0 s)
   `test`: 3 failed, 165 passed, 20 warnings, 1 error in 3.93s
6. factory: started doing as opencode-demo.
