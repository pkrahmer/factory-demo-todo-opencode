---
stage: approval
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 2
comments_read: []
handed_over: approval
claim: null
journal:
- number: 1
  speaker: human
  kind: created
  at: '2026-10-19T12:52:45.674691Z'
  stage: intake
- number: 2
  speaker: factory
  kind: started
  at: '2026-10-19T12:52:45.678194Z'
  stage: intake
- number: 3
  speaker: intake
  kind: result
  at: '2026-10-19T12:53:13.179226Z'
  stage: intake
  run: 4b6869a3d8274f9f87875fe8b28582e2
- number: 4
  speaker: factory
  kind: started
  at: '2026-10-19T12:53:33.013798Z'
  stage: tests
- number: 5
  speaker: tester
  kind: result
  at: '2026-10-19T12:54:25.555009Z'
  stage: tests
  run: 43eff077b37f4883af1d566f2ef20456
- number: 6
  speaker: factory
  kind: started
  at: '2026-10-19T12:54:46.987156Z'
  stage: doing
- number: 7
  speaker: coder
  kind: result
  at: '2026-10-19T12:55:41.439338Z'
  stage: doing
  run: f7d28482eb034c8281d3e61214ef674c
- number: 8
  speaker: factory
  kind: started
  at: '2026-10-19T12:56:01.714482Z'
  stage: review
- number: 9
  speaker: reviewer
  kind: result
  at: '2026-10-19T12:56:29.374578Z'
  stage: review
  run: 27ab09a632b94a1880a61417574b7a15
- number: 10
  speaker: factory
  kind: started
  at: '2026-10-19T12:56:49.322533Z'
  stage: docs
- number: 11
  speaker: documenter
  kind: result
  at: '2026-10-19T12:57:26.042873Z'
  stage: docs
  run: 5153312f718b402dbead327a41fd3465
- number: 12
  speaker: factory
  kind: started
  at: '2026-10-19T12:57:46.108993Z'
  stage: smoke-test
- number: 13
  speaker: smoke-tester
  kind: result
  at: '2026-10-19T12:58:03.243754Z'
  stage: smoke-test
  run: 4f94ce3c43db4b87af2aeae8cb6ade4b
---

# Service layer with filtering

## Description

Add the use-case layer on top of the domain: a `TodoService` that creates, reads, lists (all, or filtered by the done flag), renames, completes, reopens and deletes todos through the `TodoRepository` protocol. The service owns the clock, injectable for tests; the title rule stays in the domain and its errors pass through unchanged. No API yet.

## Interface

`src/app/service/todo_service.py`

```python
Clock = Callable[[], datetime]

def utc_now() -> datetime: ...

class TodoService:
    def __init__(self, repository: TodoRepository, clock: Clock = utc_now) -> None: ...
    def create(self, title: str) -> Todo: ...
    def get(self, todo_id: UUID) -> Todo: ...
    def list(self, *, done: bool | None = None) -> list[Todo]: ...
    def rename(self, todo_id: UUID, title: str) -> Todo: ...
    def complete(self, todo_id: UUID) -> Todo: ...
    def reopen(self, todo_id: UUID) -> Todo: ...
    def delete(self, todo_id: UUID) -> None: ...
```

- `create` stamps `created_at` with the clock; `list(done=None)` means no filter; every list is in the repository's order (creation order).
- Domain errors (`InvalidTitle`, `TodoNotFound`) propagate unchanged.
- `app.service` sees storage only through `TodoRepository`; import-linter (`make check`) already refuses an import of `app.repository` there. Tests use `InMemoryTodoRepository` as the concrete repository; a test may import it.

Tests: `tests/service/test_todo_service.py`, with a clock that returns a fixed time, or one that ticks a minute per call where the order must be observable.

## Acceptance criteria

1. `create("  Buy milk ")` returns a todo titled `Buy milk`, not done, whose `created_at` is the value the injected clock returned; `get` with its id returns an equal todo.
2. `create` with a blank title raises `InvalidTitle`, and `list()` is still empty afterwards.
3. `get` with an unknown id raises `TodoNotFound` carrying that id.
4. `list()` returns every todo, in creation order (a clock that ticks makes the order observable).
5. The done filter, as rows of one parametrized test over two completed and two open todos created alternately: `list(done=True)` returns only the completed todos, `list(done=False)` only the open ones, and `list(done=None)` all four, each in creation order.
6. `rename` returns the todo with the new title, stripped, and the same id, done flag and `created_at`; `get` returns the renamed todo afterwards.
7. `rename` with a blank title raises `InvalidTitle`, and `get` still returns the todo with its old title.
8. `complete` returns the todo with `done` true, and `get` returns it completed afterwards.
9. `complete` on a completed todo returns it, still done, without an error.
10. `reopen` returns the todo with `done` false, and `get` returns it open afterwards.
11. `reopen` on an open todo returns it, still open, without an error.
12. `delete` removes the todo: `get` afterwards raises `TodoNotFound`.
13. `rename`, `complete`, `reopen` and `delete` with an unknown id each raise `TodoNotFound` carrying that id: four rows of one parametrized test.
14. `utc_now()` returns a timezone-aware datetime with a zero UTC offset, no more than a second away from `datetime.now(UTC)`.
15. A `TodoService` built without a clock stamps with `utc_now`: a todo created through `TodoService(repository)` has a timezone-aware `created_at` with a zero UTC offset, no more than a second away from `datetime.now(UTC)`.
16. `make check` stays green.
17. docs: `docs/project-guide.md` describes the service layer: what `TodoService` owns (the use cases, the clock, the done filter) and that it reaches storage only through the repository protocol.

## Smoke test

```bash
uv run python -c "
from datetime import UTC, datetime
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService
svc = TodoService(InMemoryTodoRepository(), clock=lambda: datetime(2026, 10, 4, 12, 0, tzinfo=UTC))
a = svc.create('  Buy milk ')
b = svc.create('Write the next story')
svc.complete(a.id)
print([t.title for t in svc.list(done=True)])
print([t.title for t in svc.list(done=False)])
print(svc.rename(b.id, 'Write story S0003').title, svc.get(b.id).created_at.isoformat())
"
```

Expect: three lines, `['Buy milk']`, then `['Write the next story']`, then `Write story S0003 2026-10-04T12:00:00+00:00`.

```bash
uv run python -c "
from uuid import uuid4
from app.repository.memory import InMemoryTodoRepository
from app.service.todo_service import TodoService
svc = TodoService(InMemoryTodoRepository())
for call in (lambda: svc.create('   '), lambda: svc.complete(uuid4())):
    try:
        call()
    except Exception as e:
        print(type(e).__name__)
print(svc.list())
"
```

Expect: three lines, `InvalidTitle`, then `TodoNotFound`, then `[]`.

## Journal

1. 2026-10-19 human: created.
2. factory: started intake as opencode-demo.
3. intake: accepted

   - Interface: it names `src/app/service/todo_service.py` with `Clock`, `utc_now` and `TodoService`, and a signature for each method.
     - The signatures fit the code that exists. `TodoRepository` has `add`, `get`, `list_all`, `update` and `delete`. `Todo` has `new(title, now=...)`, `with_title` and `with_done`. The domain has `InvalidTitle` and `TodoNotFound(todo_id)`. `InMemoryTodoRepository` is in `app.repository.memory`.
     - `app/service` does not exist yet, so the coder creates the package.
   - Criteria: each is testable by one test function, or by one parametrized test where the story says so (5 and 13).
     - Every Interface behaviour has a criterion:
       - the clock stamps `created_at` (1);
       - `done=None` means no filter (5, with `list()` in 4);
       - lists are in creation order (4, 5);
       - errors propagate unchanged (2, 3, 7, 13);
       - the default clock is `utc_now` (15);
       - `utc_now` is timezone-aware, at zero offset and within a second of now (14).
     - Every rule has its failing side. A blank title is refused on `create` (2) and on `rename` (7), and nothing is stored or changed. An unknown id is refused on `get` (3) and on the other four methods (13). A completed todo can be completed again and an open one reopened without an error (9, 11), which is feature decision 5.
     - The 200-character title limit belongs to the domain, and the story keeps it there ("the title rule stays in the domain"), so it needs no criterion in this story.
     - One small ambiguity in criterion 5: it does not say which todos are completed ("created alternately"). It does not change what the test checks, so I did not ask.
   - Smoke test: both blocks are runnable with `uv run python -c`, and they use only `InMemoryTodoRepository` and `TodoService`.
     - Block 1: the fixed clock gives every todo the same time, but each filtered list holds one todo, so tie-breaking by id does not matter. The expected lines `['Buy milk']`, `['Write the next story']` and `Write story S0003 2026-10-04T12:00:00+00:00` follow from the Interface.
     - Block 2: it prints `InvalidTitle`, `TodoNotFound` and `[]`, which can be checked line by line.
   - Architecture: the service depends on the `TodoRepository` protocol and the domain only, with no import of `app.repository` or `app.api`. The clock lives in the service, as the Description says. Tests go in `tests/service/` and use the in-memory repository, as `CLAUDE.md` asks. There are no new dependencies and no change to `factory/`.
   - Scope: this is the "service layer: create, get, list with a done filter, rename, complete, reopen, delete" item of `feature.md`, with no API and no storage change. Nothing is in "Out of scope". Feature decisions 5 and 17 are carried by criteria 9, 11 and 5.
4. factory: started tests as opencode-demo.
5. tester: I wrote the service tests against the Interface. The concrete repository is `InMemoryTodoRepository`. One fixture uses a clock fixed at 2026-10-04 12:00 UTC. A second uses a clock that moves a minute ahead on every call, for the tests where order must be visible. The blank-title criteria have two rows each, an empty title and one of only spaces. The 200-character title limit is not tested here: the Interface does not state it, and it stays in the domain, which already tests it. No criterion needed interpreting.

   - criterion 1: tests/service/test_todo_service.py::test_create_strips_the_title_and_stamps_the_clock
   - criterion 2: tests/service/test_todo_service.py::test_create_with_a_blank_title_is_rejected_and_stores_nothing
   - criterion 3: tests/service/test_todo_service.py::test_get_with_an_unknown_id_is_not_found
   - criterion 4: tests/service/test_todo_service.py::test_list_returns_every_todo_in_creation_order
   - criterion 5: tests/service/test_todo_service.py::test_list_filters_by_the_done_flag (rows done, open, all)
   - criterion 6: tests/service/test_todo_service.py::test_rename_changes_only_the_title
   - criterion 7: tests/service/test_todo_service.py::test_rename_with_a_blank_title_is_rejected_and_keeps_the_old_title
   - criterion 8: tests/service/test_todo_service.py::test_complete_marks_the_todo_done
   - criterion 9: tests/service/test_todo_service.py::test_completing_a_completed_todo_keeps_it_done
   - criterion 10: tests/service/test_todo_service.py::test_reopen_marks_the_todo_open
   - criterion 11: tests/service/test_todo_service.py::test_reopening_an_open_todo_keeps_it_open
   - criterion 12: tests/service/test_todo_service.py::test_delete_removes_the_todo
   - criterion 13: tests/service/test_todo_service.py::test_changing_an_unknown_id_is_not_found (rows rename, complete, reopen, delete)
   - criterion 14: tests/service/test_todo_service.py::test_utc_now_is_the_current_time_in_utc
   - criterion 15: tests/service/test_todo_service.py::test_service_without_a_clock_stamps_the_current_utc_time
   - criteria 16 and 17 (`make check`, docs) have no test of their own.

   Files created: tests/service/__init__.py, tests/service/test_todo_service.py. No earlier test file was changed.

   Could not import: `app.service.todo_service`, because the `app.service` package does not exist yet. That is the expected red: `make test` gave 56 passed and 1 import error, in tests/service/test_todo_service.py. `make lint` is green.

   `lint`: lint: green (0.0 s)
   `test`: 56 passed, 1 error in 1.62s
6. factory: started doing as opencode-demo.
7. coder: I added the service layer. `make check` is green: 78 tests passed and coverage is 100 %. The first smoke-test block prints the three expected lines.

   What I built:
   - `src/app/service/__init__.py`: the new package, holding only its module docstring.
   - `src/app/service/todo_service.py`: `Clock`, `utc_now()`, which returns `datetime.now(UTC)`, and `TodoService`, with the signatures the Interface gives.
     - `create` builds the todo with `Todo.new(title, now=clock())` and then stores it with `add`. A bad title fails before anything is stored, so the domain's `InvalidTitle` reaches the caller unchanged.
     - `get` and `delete` hand straight on to the repository, which raises `TodoNotFound` itself.
     - `list(done=None)` returns `list_all()` as it comes, so the order is the repository's. With `done` set, it keeps only the todos with that flag, in the same order.
     - `rename`, `complete` and `reopen` each read the todo, change it with `with_title` or `with_done`, and then pass it to a private `_store` helper. `_store` calls `update` and returns the changed todo.

   Main design decision: the done filter runs in the service, over `list_all()`. The alternative I rejected was adding a filtered list method to the `TodoRepository` protocol. That would change the domain protocol and the in-memory repository, which is outside this story, and the Interface gives the filter to the service.

   Refactor pass: I read my own diff. The only cleanup needed was the `_store` helper, so that the three update methods do not each repeat "update, then return". Nothing else needed changing.

   Noticed but not touched:
   - The method name `list` hides the built-in `list` inside the class body. Its own return annotation still works, and mypy is happy. Any later method in the class that needs a `list[...]` annotation would run into this, though.
   - No journal entry changed the meaning of the task, so I left `## Description` as it was.
   - I did not write the docs criterion (`docs/project-guide.md`): that file belongs to the documenter stage.

   `check`: check: green
   `duplicates`: duplicates: 0 similar code, 6 dead code, in .reports/
8. factory: started review as opencode-demo.
9. reviewer: no findings

   What I reviewed: the diff from main, excluding `factory/` (`src/app/service/__init__.py`, `src/app/service/todo_service.py`, `tests/service/__init__.py`, `tests/service/test_todo_service.py`), plus the work item.

   - **Acceptance criteria:** each of criteria 1–15 has a test in `tests/service/test_todo_service.py`, and each test checks what its criterion says.
     - Criterion 5 is one parametrized test with rows done, open and all, over todos created alternately.
     - Criterion 13 is one parametrized test with four rows, and each row checks the id carried by `TodoNotFound`.
     - Both blank-title rules test their refused side, with the rows empty and spaces. After the refusal, the tests check that nothing was stored (criterion 2) and that the old title is kept (criterion 7).
     - Criteria 14 and 15 compare `utcoffset()` with `timedelta(0)`. A naive datetime fails that check, so timezone awareness is tested too.
     - The Interface states no limit of its own. The 200-character title rule stays in the domain and is tested there.
     - The factory's `make check` after the coder was green (entry 7).
   - **Architecture:** `app.service.todo_service` imports only `app.domain.model`, `app.domain.repository` and the standard library. It reaches storage only through the `TodoRepository` protocol. Only the test imports `InMemoryTodoRepository`, which the Interface allows.
   - **Security:** no secrets, no shell or SQL, and no markers that silence a check.
   - **Quality:**
     - Every public name in `app.service` has a docstring, and each says what the code does.
     - `_store` removes the repeated "update, then return" from the three update methods.
     - The done filter compares `todo.done is done`, keeps the repository's order, and leaves the protocol unchanged.
     - The method name `list` hides the built-in, but its own `-> list[Todo]` annotation is evaluated before the name is bound, so it still means the built-in.
     - There is no copied helper. `TickingClock` and `_assert_utc_close_to_now` exist nowhere else under `tests/`. `T0` is a test-data constant that the domain and repository test modules each define too, not a helper.
   - **Work item hygiene:** entry 7 explains the main decision and the alternative it rejected: filtering in the service rather than adding a filtered list method to the protocol. The Description matches what was built, and criterion 17 still says what `docs/project-guide.md` must cover.

   Earlier tests: none. Every test file in the diff is new (status `A`), and no test file that `main` already holds was changed.
10. factory: started docs as opencode-demo.
11. documenter: I documented the service layer. I did not run `make check`: I changed only documents, and the factory runs it after me. I ran the story's first smoke-test block, which I added to the guide, and it printed the three expected lines.

    Files changed:
    - `docs/project-guide.md`:
      - The "Built so far" line now includes the service layer.
      - A new `## Service` section gives a method table and says what `TodoService` owns: the use cases, the clock (`Clock`, `utc_now`) and the done filter. It says the service reaches storage only through the repository protocol and never imports `app.repository`. It also says the filter runs in the service over `list_all()`, and that a filter the database should apply means extending the protocol.
      - "Try it" gains a second example, run through the service.
    - `README.md`: the "Where to look next" line for `docs/project-guide.md` now mentions the service.

    Cross-read and found current: the layers table, the layer rules, the domain model, errors, repository protocol and in-memory repository sections of `docs/project-guide.md`, and the `app.service` row of the layers table, which already matched the code. I also compared the Interface with `src/app/service/todo_service.py`. They agree, and the module, class, `utc_now` and public-method docstrings are present. I found no findings for the coder.

    Stale text I noticed but did not touch:
    - `CLAUDE.md` names `docs/api.md` and `docs/decisions.md`, which do not exist yet. They presumably come with later stories, and `CLAUDE.md` is not mine to edit.
    - The method name `list` hides the built-in inside the class body. The coder and the reviewer both noted it. It is harmless today and is not a documentation matter.

    `check`: check: green
12. factory: started smoke-test as opencode-demo.
13. smoke-tester: I ran both smoke-test commands from the repository root, exactly as written and in order. Neither starts a server. Both printed what their `Expect:` line says, and both exited with code 0. I fixed nothing and did not run `make check`, since the factory runs it after this stage.

    Command 1 (fixed clock: create, complete, filter, rename):

    ```
    ['Buy milk']
    ['Write the next story']
    Write story S0003 2026-10-04T12:00:00+00:00
    ```

    Met its `Expect:` line. The three lines are, in order, `['Buy milk']`, `['Write the next story']` and `Write story S0003 2026-10-04T12:00:00+00:00`.

    Command 2 (a blank title, then an unknown id, then an empty list):

    ```
    InvalidTitle
    TodoNotFound
    []
    ```

    Met its `Expect:` line. The three lines are, in order, `InvalidTitle`, `TodoNotFound` and `[]`.

    Against the acceptance criteria:
    - The output agrees with these criteria:
      - 1: the title is stripped (`Buy milk`), and `created_at` is the time the clock returned (`2026-10-04T12:00:00+00:00`).
      - 2: a blank title raises `InvalidTitle`, and `list()` is still `[]` afterwards.
      - 5: `done=True` and `done=False` each return only their own todos.
      - 6: the rename returns the stripped new title, and `get` shows the same `created_at`.
      - 8: `complete` marks the todo done, since it shows up under `done=True`.
      - 13: `complete` with an unknown id raises `TodoNotFound`.
      - 15: a service built without a clock creates and lists without error.
    - The output contradicts no criterion.
    - The output does not exercise these criteria: 3, 4 (creation order with a clock that ticks), 9–12 and 14. Their tests and `make check` cover them.

    Findings: none.
