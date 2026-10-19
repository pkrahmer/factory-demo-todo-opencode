---
stage: smoke-test
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 8
comments_read: []
handed_over: null
claim: null
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
- number: 7
  speaker: coder
  kind: result
  at: '2026-10-19T13:52:57.180357Z'
  stage: doing
  run: 4ba2596cb4e8418e93cb84179042c01c
- number: 8
  speaker: factory
  kind: started
  at: '2026-10-19T13:53:17.375314Z'
  stage: review
- number: 9
  speaker: reviewer
  kind: result
  at: '2026-10-19T13:53:42.045339Z'
  stage: review
  run: 562e46f4e7324487848210a086587335
- number: 10
  speaker: factory
  kind: started
  at: '2026-10-19T13:54:02.767874Z'
  stage: docs
- number: 11
  speaker: documenter
  kind: result
  at: '2026-10-19T13:55:02.458884Z'
  stage: docs
  run: e263f6d5cde94a8bbcb3c4fb4941e969
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
7. coder: Built `GET /stats`, which returns the open, done and total counts of the todos. `make check` is green with 173 tests passing, and no test was changed.

   - `src/app/service/todo_service.py`: added the frozen, slotted dataclass `TodoStats(open, done)`. `total` is a property that returns `open + done`. Added `TodoService.stats()`, which calls `list_all` once, counts the done todos and works out the open count as the list length minus the done count. The module docstring now also mentions counting.
   - `src/app/api/schemas.py`: added `StatsRead(open, done, total)` with `from_stats`. It imports `TodoStats` from the service, which the layers allow (api → service).
   - `src/app/api/stats.py` (new): `router = APIRouter(tags=["stats"])` with `GET /stats`, which uses the existing `Service` dependency.
   - `src/app/api/app.py`: `create_app` includes `stats.router` after the health router.
   - `docs/openapi.json`: regenerated with `make openapi`.

   Main decision: count over a single `list_all` result in the service. I rejected a repository count query or a new protocol method, because the Description rules out new repository methods and criterion 5 requires exactly one `list_all` call. I also rejected filtering the list twice, once for open and once for done, because the Interface asks for one pass.

   Refactor: I read my diff back and nothing needed changing. The journal did not change what the task means, so I left `## Description` as it is.

   Noticed but not touched: `docs/api.md` (criterion 10) belongs to the documenter stage. Every test run prints a StarletteDeprecationWarning about `httpx` in the test client. It was there before this work and is outside this work item.

   `check`: check: green
   `duplicates`: duplicates: 0 similar code, 8 dead code, in .reports/
8. factory: started review as opencode-demo.
9. reviewer: no findings

   Reviewed `git diff main...HEAD -- . ':!factory'` against the work item.
   - Criteria 1 to 8 each have a test that checks what the criterion says. Criteria 1 to 5 are in tests/service/test_stats.py, criteria 6 and 7 in tests/api/test_stats.py, and criterion 8 is the existing tests/api/test_openapi.py::test_committed_schema_matches_the_app, with docs/openapi.json regenerated. Criterion 6 is one parametrized test with two rows, run through TestClient against create_app. The Interface states no limit, validation or error, so there is no refused side to test. The coder's journal (entry 7) records `make check` green.
   - Architecture: `TodoService.stats` uses only the repository protocol's `list_all` and counts in one pass. `TodoStats` is a frozen, slotted dataclass in app.service with a docstring, and `total` is a property. app.api.schemas imports TodoStats from app.service, which the layer order allows (api → service). The router uses the existing `Service` dependency and is included in `create_app`. Domain and repository are untouched.
   - Security: there are no secrets and no strings built into commands or queries, and no check is silenced by a marker or a baseline entry.
   - Quality: names are clear and there is no dead code. `CountingRepository` is new; no counting fake already exists under tests/. The new test data reuses `make_todo` and `TickingClock` from tests/fakes.py.
   - Hygiene: the journal names the main decision (one `list_all` and one pass) and what was rejected (a repository count method, filtering twice). The Description matches what was built, and criterion 10 still names what docs/api.md must say.

   Earlier tests changed:
   - tests/api/test_health.py: standing leave to move a shared test helper (the `HTTP_METHODS` constant moved to tests/fakes.py; every test keeps its name and what it checks).
   - tests/api/test_openapi.py: standing leave to move a shared test helper (the same `HTTP_METHODS` move; every test keeps its name and what it checks).
   - tests/fakes.py: standing leave to move a shared test helper (it receives the moved `HTTP_METHODS` constant; nothing else changed).
10. factory: started docs as opencode-demo.
11. documenter: Documented `GET /stats` for the reader who was not there. The code matches the Interface and the criteria (`TodoStats` is frozen with `total` as a property, `stats()` makes one `list_all` call, `StatsRead.from_stats`, the router tagged `stats`, `create_app` includes it), so there are no findings for the coder.

    Files changed:
    - `docs/api.md`: added a `GET /stats` row to the endpoint table (criterion 10) and a "Stats" section with the three fields, the empty case, the fact that counts are not cached, the tag and one curl example. Added the `/health` row to the same table: the endpoint was documented below the table but missing from it.
    - `docs/project-guide.md`: added `stats()` to the service table and "The counts" to what the service owns (frozen slotted `TodoStats`, `total` a property, one `list_all` call, why the count is in the service). Added `StatsRead` and the `stats` module to the API module table and said that `create_app` includes the stats router.
    - `README.md`: added a `/stats` curl example in "Getting started" and updated the "Where to look next" pointers.

    Run: the story's smoke test printed `{'open': 2, 'done': 1, 'total': 3}` with status 200, and an empty app gave all zeros, matching what the docs say. The curl commands are the same requests through a running server. I did not run `make check`: only documents changed, and the factory's checks decide.

    Cross-read and found current: `docs/openapi.json` (generated, matches the code, covered by the existing test), the rest of `docs/api.md` (errors, title and PATCH rules, storage, health) and the rest of `docs/project-guide.md` (layers, domain, repositories, composition root).

    Stale or missing, not mine to fix: `docs/decisions.md`, which `CLAUDE.md` names, does not exist yet. Nothing in this story needed a lasting reason, so I did not create it. Every test run prints a Starlette deprecation warning about `httpx`; the coder noted it too, and it is unrelated.

    `check`: check: green
