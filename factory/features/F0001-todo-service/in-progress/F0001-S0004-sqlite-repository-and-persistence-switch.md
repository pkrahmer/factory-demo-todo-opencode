---
stage: smoke-test
blocked: null
round: 1
attempts: 0
crashes: 0
pull_request: 4
comments_read: []
handed_over: null
claim:
  instance: opencode-demo
  stage: smoke-test
  started_at: '2026-10-19T13:21:49.709345Z'
  lease_duration: 60
journal:
- number: 1
  speaker: human
  kind: created
  at: '2026-10-19T13:12:27.345955Z'
  stage: intake
- number: 2
  speaker: factory
  kind: started
  at: '2026-10-19T13:12:27.349326Z'
  stage: intake
- number: 3
  speaker: intake
  kind: result
  at: '2026-10-19T13:12:56.688256Z'
  stage: intake
  run: e71ef93ad74949288816f2c68857078c
- number: 4
  speaker: factory
  kind: started
  at: '2026-10-19T13:13:16.622475Z'
  stage: tests
- number: 5
  speaker: tester
  kind: result
  at: '2026-10-19T13:14:51.621368Z'
  stage: tests
  run: baaa7380b8204b1ebc93551a3b149e50
- number: 6
  speaker: factory
  kind: started
  at: '2026-10-19T13:15:12.155369Z'
  stage: doing
- number: 7
  speaker: coder
  kind: result
  at: '2026-10-19T13:16:27.076349Z'
  stage: doing
  run: 01c39c026a3946fbb90546ad85a1237d
- number: 8
  speaker: factory
  kind: started
  at: '2026-10-19T13:16:47.598910Z'
  stage: review
- number: 9
  speaker: reviewer
  kind: result
  at: '2026-10-19T13:17:24.268290Z'
  stage: review
  run: 5293fbd7c0ef4fb591fce01bf699ded4
- number: 10
  speaker: factory
  kind: started
  at: '2026-10-19T13:17:44.447022Z'
  stage: doing
- number: 11
  speaker: coder
  kind: result
  at: '2026-10-19T13:18:45.026304Z'
  stage: doing
  run: 3742b0e691214c26a598f6a49a3f1df0
- number: 12
  speaker: factory
  kind: started
  at: '2026-10-19T13:19:05.567989Z'
  stage: review
- number: 13
  speaker: reviewer
  kind: result
  at: '2026-10-19T13:19:29.770721Z'
  stage: review
  run: 80ced7fffb604eff9bbf70fe03948009
- number: 14
  speaker: factory
  kind: started
  at: '2026-10-19T13:19:50.013263Z'
  stage: docs
- number: 15
  speaker: documenter
  kind: result
  at: '2026-10-19T13:21:29.108496Z'
  stage: docs
  run: a422ee5b5fa2421f9f27a5e21c700a74
- number: 16
  speaker: factory
  kind: started
  at: '2026-10-19T13:21:49.709345Z'
  stage: smoke-test
---

# SQLite repository and persistence switch

## Description

Add the second `TodoRepository`, backed by a SQLite file through SQLAlchemy Core, prove it equal to the in-memory one by running the existing repository contract suite against both, and let the composition root choose the repository from the environment: `TODO_DB=<path>` keeps the todos in that file across restarts, no `TODO_DB` (or an empty one) keeps them in memory as today. Nothing above the repository layer changes except `src/app/api/main.py`.

## Interface

`src/app/repository/sqlite.py`

```python
class SqliteTodoRepository:   # satisfies TodoRepository structurally, no inheritance
    def __init__(self, engine: Engine) -> None: ...
    @classmethod
    def from_path(cls, path: str | Path) -> "SqliteTodoRepository": ...
```

- `__init__` creates the table `todos` when it is missing and leaves an existing one and its rows alone.
- `from_path` opens the SQLite file at `path` (`sqlite:///<path>`), creating the file when it does not exist.
- The table is a `sqlalchemy.Table` (Core, no ORM models): `id` TEXT primary key (the UUID's hyphenated form), `title` TEXT NOT NULL, `done` BOOLEAN NOT NULL, `created_at` TEXT NOT NULL (ISO 8601, UTC). Every statement is built from Core constructs on that table; no SQL in strings (the semgrep rule `project-no-sql-text` of `make sast` refuses `sqlalchemy.text` and `exec_driver_sql`).

`src/app/api/main.py`

```python
def build_repository(environ: Mapping[str, str]) -> TodoRepository: ...
app = create_app(TodoService(build_repository(os.environ)))
```

- `TODO_DB` missing or empty: `InMemoryTodoRepository()`. Otherwise `SqliteTodoRepository.from_path(environ["TODO_DB"])`.
- `app.api.main` stays the only `app.api` module that imports `app.repository`.

Tests: by the human's leave, the tester adds one factory to the list of repository factories in `tests/repository/test_contract.py` (F0001-S0001), which returns `SqliteTodoRepository.from_path(tmp_path / "todo.db")` for the `tmp_path` the fixture passes it, so the whole contract suite runs against both repositories, and adds `SqliteTodoRepository` to that file's list of repository classes, so its no-inheritance test has a row for it; nothing else in that file changes, except a move of a shared test helper under the standing leave of `CLAUDE.md`. The other tests go into `tests/repository/test_sqlite.py` and `tests/api/test_main.py`.

## Acceptance criteria

1. Every test of the repository contract suite passes for `SqliteTodoRepository` on a file under `tmp_path`, as it does for `InMemoryTodoRepository`.
2. `from_path` on a path whose file does not exist creates the file, and the new repository's `list_all()` returns `[]`.
3. A todo added through one `SqliteTodoRepository` is returned by `get` and by `list_all` of a second instance opened on the same path.
4. A second `SqliteTodoRepository` built on the same engine does not fail, and the todos stored through the first are still there.
5. `created_at` survives the round trip: a todo created at `datetime(2026, 10, 4, 12, 0, 0, 123456, tzinfo=UTC)` is read back equal, timezone-aware, with a zero UTC offset.
6. A title containing quotes and SQL, `Robert'); DROP TABLE todos;--`, is stored and read back verbatim, and every other todo is still listed.
7. The switch on both sides, as rows of one parametrized test: `build_repository({})` and `build_repository({"TODO_DB": ""})` each return an `InMemoryTodoRepository`; `build_repository({"TODO_DB": <a path under tmp_path>})` returns a `SqliteTodoRepository`, and the file exists afterwards.
8. A todo created through `create_app(TodoService(build_repository({"TODO_DB": p})))` is listed by a second app built the same way on the same `p`.
9. An app built with `build_repository({})` writes no file: after creating a todo through it, the current directory (a `tmp_path` the test changes into with `monkeypatch.chdir`) is still empty.
10. `SqliteTodoRepository` is not a subclass of `TodoRepository`: its row of the no-inheritance test in `tests/repository/test_contract.py`, beside the row of `InMemoryTodoRepository`.
11. The stored format: a row of `todos` read back with a Core `select` has `id == str(todo.id)` (hyphenated); `created_at` a `str` that ends with `+00:00` and that `datetime.fromisoformat` reads back equal to the todo's `created_at`, also for a todo created with another offset; and `done` a `bool`, `True` for a completed todo and `False` for an open one (rows of one parametrized test).
12. `from_path(path)` and `from_path(str(path))` each open the same file and see the todos written through the other, as rows of one parametrized test.
13. `app.api.main` is still the only `app.api` module that imports `app.repository`, now that it imports `app.repository.sqlite` too: F0001-S0003's import test in `tests/api/test_imports.py` still passes.
14. `make check` stays green.
15. docs: `docs/api.md` explains storage in a short section: with `TODO_DB=<path>` the todos live in that SQLite file, created on first start; without it, or with it empty, they live in memory and are gone on restart. The README's *Getting started* shows starting the server with `TODO_DB`.

## Smoke test

```bash
d=$(mktemp -d); trap 'kill $pid 2>/dev/null; wait $pid 2>/dev/null; rm -rf "$d"' EXIT
TODO_DB="$d/todo.db" uv run uvicorn app.api.main:app --port 8765 >"$d/uvicorn.log" 2>&1 & pid=$!
for i in $(seq 40); do curl -s -o /dev/null localhost:8765/todos && break; sleep 0.5; done
curl -s -X POST localhost:8765/todos -H 'content-type: application/json' -d '{"title":"Survive a restart"}'; echo
kill $pid; wait $pid 2>/dev/null
TODO_DB="$d/todo.db" uv run uvicorn app.api.main:app --port 8765 >"$d/uvicorn.log" 2>&1 & pid=$!
for i in $(seq 40); do curl -s -o /dev/null localhost:8765/todos && break; sleep 0.5; done
curl -s localhost:8765/todos; echo
test -f "$d/todo.db" && echo "database file exists"
```

Expect: three lines: the created todo as JSON with `"title":"Survive a restart"`; then a list holding exactly that todo, with the same id, after the restart; then `database file exists`.

## Journal

1. 2026-10-19 human: created.
2. factory: started intake as opencode-demo.
3. intake: accepted

   - Interface: it names concrete modules and signatures. `src/app/repository/sqlite.py` has `SqliteTodoRepository(engine)` and `from_path(path: str | Path)`. `src/app/api/main.py` has `build_repository(environ: Mapping[str, str]) -> TodoRepository` and the module-level `app`. The table's columns, their types and the stored formats are spelled out. The change to `tests/repository/test_contract.py` (one factory, one class row) is named, with the human's leave and the standing helper-move leave. That file already has `REPOSITORY_FACTORIES` and `REPOSITORY_CLASSES` for the rows to go into.
   - Criteria: each is testable by one test function or one parametrized test.
     - Every behaviour the Interface comments state has a criterion. `__init__` creating the table and leaving rows alone is criterion 4. Creating the file is criterion 2. Reading the same file back through a second instance is criterion 3. The `str` and `Path` forms of `from_path` are criterion 12. The stored formats are criterion 11, with `id`, `created_at` and `done` as separate rows and another offset covered. The `TODO_DB` rule is criterion 7, with the missing, empty and set sides as rows. No file for an in-memory app is criterion 9. Import isolation is criterion 13. The no-inheritance rule is criterion 10.
     - Both sides of each rule are covered. Missing or empty `TODO_DB` against set is criterion 7. Persisting against not writing a file is criteria 8 and 9. SQL-hostile input is criterion 6. The refused sides of the repository rules (`DuplicateTodo`, `TodoNotFound`, ordering) are held by the existing contract suite through criterion 1.
     - The `title` and `done` NOT NULL constraints and the ordering across second boundaries are not separate criteria. The first is not an Interface behaviour that can fail through the repository's API. The second is the protocol's rule, already tested in the contract suite. I did not count either as a gap.
   - Smoke test: the commands are runnable. They use a temporary directory, start uvicorn twice on port 8765 with the same `TODO_DB`, create a todo, restart, list, and test that the file exists. The `Expect:` line is checkable: three lines, the created JSON with the title, a list with the same id after the restart, and `database file exists`.
   - Architecture: the placement fits `CLAUDE.md`.
     - `app.repository.sqlite` implements the protocol structurally, imports only `app.domain` plus SQLAlchemy Core, and uses no ORM or SQL strings. This is consistent with the `project-no-sql-text` semgrep rule.
     - Wiring stays in `app.api.main`, the only `app.api` module that imports `app.repository`. Criterion 13 holds that through the existing `tests/api/test_imports.py`.
     - `app.domain` and `app.service` are untouched.
   - Scope: it is within feature F0001. The scope lists the SQLite repository behind the same protocol, the contract suite and the persistence switch, and decisions 8, 14, 15 and 16 of `feature.md` are all reflected in the criteria. Nothing in "Out of scope" is touched.
4. factory: started tests as opencode-demo.
5. tester: Wrote the tests for every acceptance criterion against the Interface. All the new tests fail to import because the modules under test don't exist yet. `make lint` is green. I skipped the type check, as this stage says to.

   Criterion → test:
   - criterion 1: tests/repository/test_contract.py, the whole suite. `REPOSITORY_FACTORIES` gains `_sqlite`, which returns `SqliteTodoRepository.from_path(tmp_path / "todo.db")`.
   - criterion 2: tests/repository/test_sqlite.py::test_from_path_creates_a_missing_file_and_starts_empty
   - criterion 3: tests/repository/test_sqlite.py::test_todo_is_seen_by_a_second_instance_on_the_same_path
   - criterion 4: tests/repository/test_sqlite.py::test_second_instance_on_the_same_engine_keeps_the_stored_todos
   - criterion 5: tests/repository/test_sqlite.py::test_created_at_survives_the_round_trip
   - criterion 6: tests/repository/test_sqlite.py::test_title_with_quotes_and_sql_is_stored_verbatim
   - criterion 7: tests/api/test_main.py::test_todo_db_chooses_the_repository (rows: missing, empty, set)
   - criterion 8: tests/api/test_main.py::test_todos_persist_across_apps_on_the_same_file
   - criterion 9: tests/api/test_main.py::test_in_memory_app_writes_no_file
   - criterion 10: tests/repository/test_contract.py::test_repository_does_not_inherit_the_protocol, with a new `SqliteTodoRepository` row in `REPOSITORY_CLASSES`.
   - criterion 11: tests/repository/test_sqlite.py::test_stored_row_has_the_documented_format (rows: open-utc, done-utc, open-other-offset). It reads the `todos` table back through a reflected Core `Table` and `select`, so it doesn't depend on what the module calls its table object.
   - criterion 12: tests/repository/test_sqlite.py::test_path_and_str_open_the_same_file (rows: path-then-str, str-then-path)
   - criterion 13: the existing tests/api/test_imports.py::test_only_main_imports_the_repository_layer, left unchanged.
   - criteria 14 and 15: not tests. They are covered by `make check` and the docs stage.

   Files created: tests/repository/test_sqlite.py, tests/api/test_main.py, tests/conftest.py (the `db_path` fixture, `tmp_path / "todo.db"`, which both new modules use).

   Earlier test files changed:
   - tests/repository/test_contract.py: changed with the human's leave in the Interface (the `_sqlite` factory and the `SqliteTodoRepository` class row).
   - Also in test_contract.py, under the standing leave in CLAUDE.md for moving a shared helper: `make_todo` and its copy of `T0` moved to tests/fakes.py, where `T0` already existed with the same value. test_contract.py now imports both from there. Every contract test keeps its name and checks the same thing.
   - tests/fakes.py: gains `make_todo`.

   Rejected: moving the `T0` copy in tests/domain/test_model.py. Nothing in this story needs it.

   Modules the test runner could not import:
   - `app.repository.sqlite`, in tests/repository/test_contract.py, tests/repository/test_sqlite.py and tests/api/test_main.py.
   - `build_repository` from `app.api.main`, in tests/api/test_main.py.

   Open: nothing.

   `lint`: lint: green (0.0 s)
   `test`: 109 passed, 20 warnings, 3 errors in 3.31s
6. factory: started doing as opencode-demo.
7. coder: Built:
   - `src/app/repository/sqlite.py` (new): `SqliteTodoRepository`.
     - The `todos` table is a Core `Table` with the four columns the Interface names: `id`, `title`, `done`, `created_at`.
     - `__init__` runs `create_all(checkfirst=True)`, so an existing table and its rows are left alone.
     - `from_path` builds a `sqlite:///<path>` engine.
     - Every statement is a Core `insert`/`select`/`update`/`delete`, with no SQL in strings.
     - A duplicate id is caught as `IntegrityError` and raised as `DuplicateTodo`.
     - `update` or `delete` that touches no row raises `TodoNotFound`.
   - `src/app/api/main.py`: `build_repository(environ)` returns `InMemoryTodoRepository()` when `TODO_DB` is missing or empty, and `SqliteTodoRepository.from_path(...)` otherwise. `app = create_app(TodoService(build_repository(os.environ)))`.
   - `make openapi` was run; `docs/openapi.json` is unchanged.
   - `make check` is green: 146 passed, 100% coverage.

   Main decision: the database sorts the list itself (`ORDER BY created_at, id`).
   - `created_at` is stored in a fixed-width form, `%Y-%m-%dT%H:%M:%S.%f+00:00`: microseconds always written, offset always `+00:00`. Text order is then time order.
   - The hyphenated UUID text is also fixed-width lowercase hex, so its text order is the UUID order.
   - One helper, `_with_todo_values`, sets the column values for both insert and update. It is a generic over `Insert | Update`, so no bare dict crosses a function boundary.
   - Rejected: `isoformat()` plus sorting in Python. `isoformat()` leaves out the microseconds when they are zero, so the stored text would not sort by time. Sorting in Python would also duplicate the in-memory repository's sort.

   Refactor: I read the diff once. Nothing needed changing beyond what was already done while getting the checks green: `Any` replaced by `Update | Delete` on the one-row helper, and a PEP 695 type parameter that ruff's UP047 asks for.

   Noticed, not touched:
   - `_todo_from_row` takes `Row[Any]`, since that is what SQLAlchemy returns for a `select` on a `Table`. The `Todo` constructor checks the values right away.
   - `TestClient` emits a Starlette deprecation warning about `httpx`; it was already there before this story.
   - Each `from_path` creates its own engine and never disposes it. That is harmless for a long-running server and for the tests.

   Description unchanged: no journal entry changed the meaning of the task.

   `check`: check: green
   `duplicates`: duplicates: 0 similar code, 6 dead code, in .reports/
8. factory: started review as opencode-demo.
9. reviewer: Findings:
   1. `src/app/repository/sqlite.py`, `_todo_from_row(row: Row[Any])` and `from typing import Any`: this breaks the rule in `CLAUDE.md` *Architecture*, "`Any` only at a boundary that Pydantic validates immediately". The row comes from SQLAlchemy, and the `Todo` dataclass is built from it, not a Pydantic model, so the column values go untyped into the domain. Fix: type the row as `Row[tuple[str, str, bool, str]]`, unpack its typed values (`id_, title, done, created_at = row.tuple()`) to build the `Todo`, and drop the `Any` import.

   I stopped at the Architecture group. The acceptance criteria group passed: criteria 1–13 each have a test that checks what the criterion says, the failing sides of the Interface rules are covered, and the coder's entry 7 reports `make check` green.

   Earlier tests changed:
   - tests/repository/test_contract.py: the human's leave in the story's Interface (the `_sqlite` factory, the `SqliteTodoRepository` row in `REPOSITORY_CLASSES`) and the standing leave in `CLAUDE.md` to move a shared helper (`make_todo` and the copied `T0` now come from `tests/fakes.py`). Every test keeps its name and what it checks.
   - tests/fakes.py: the standing leave to move a shared helper (gains `make_todo`, moved from test_contract.py). Nothing already in the file changed.
10. factory: started doing as opencode-demo.
11. coder: Fixed the review finding in `src/app/repository/sqlite.py`. `make check` is green: 146 passed, 100% coverage.

    What I built:
    - `_todo_from_row` now takes `Row[str, str, bool, str]` instead of `Row[Any]`.
    - It unpacks the four typed column values (`stored_id, title, done, created_at = row`) and builds the `Todo` from them.
    - The `from typing import Any` import is gone.
    - Nothing else changed.

    Main decision: I spelled the row type the SQLAlchemy 2.1 way.
    - The reviewer suggested `Row[tuple[str, str, bool, str]]` with `row.tuple()`. I tried it and `mypy --strict` refused the unpacking ("Need more than 1 value to unpack").
    - The project uses SQLAlchemy 2.1.5, where `Row` takes each column type as a separate parameter (`Generic[Unpack[_Ts]]`). In this version `Row` behaves like a tuple and can be unpacked directly.
    - So the column types go in as separate parameters, with no `.tuple()` call. Rejected: the reviewer's exact spelling, because it does not pass the type check on 2.1.

    Refactor: I read the diff once and nothing needed changing.

    Noticed, not touched:
    - The unpacking depends on the order of the columns in `_todos` (`id`, `title`, `done`, `created_at`). The table and the helper sit side by side in the same module.
    - `select(_todos)` gives an untyped row, so mypy accepts the typed annotation but cannot prove the types match. If a column changed type, only the tests would catch it, not the type check.

    Description unchanged: no journal entry changed the meaning of the task.

    `check`: check: green

    `check`: check: green
    `duplicates`: duplicates: 0 similar code, 6 dead code, in .reports/
12. factory: started review as opencode-demo.
13. reviewer: no findings

    The fix for round 0's finding holds. `_todo_from_row` in `src/app/repository/sqlite.py` now takes `Row[str, str, bool, str]` and unpacks the typed values. The `Any` import is gone, so the `Any` rule in `CLAUDE.md` *Architecture* holds.

    The rest of the diff is as reviewed in round 0:
    - Acceptance criteria 1–13 each have a test that checks what the criterion says. The missing, empty and set sides of `TODO_DB` are rows of one parametrized test, and the contract suite runs against both repositories. The coder's entry 11 reports `make check` green.
    - The layers hold: wiring stays in `app.api.main`, and the repository implements the protocol structurally.
    - Every statement is a Core construct, with no SQL in strings and no marker that silences a check.
    - The Description matches what was built, and the docs criterion is still current.

    Earlier tests changed:
    - tests/repository/test_contract.py: the human's leave in the story's Interface (the `_sqlite` factory and the `SqliteTodoRepository` row in `REPOSITORY_CLASSES`), plus the standing leave in `CLAUDE.md` to move a shared helper (`make_todo` and the copy of `T0` now come from `tests/fakes.py`). Every test keeps its name and what it checks.
    - tests/fakes.py: the standing leave to move a shared helper (`make_todo` moved in). Nothing already in the file changed.
14. factory: started docs as opencode-demo.
15. documenter: Wrote the documentation for the SQLite repository and the `TODO_DB` switch. I found nothing in the diff that contradicts the Interface or the criteria. No findings for the coder.

    Files changed:
    - `docs/api.md`: added a *Storage* section, as the docs criterion asks.
      - It covers `TODO_DB=<path>` (SQLite file, created on first start, survives a restart) and `TODO_DB` unset or empty (in memory, gone on restart).
      - It also covers the stored table and columns, and the formats of `created_at` and `id`.
      - I ran two things and wrote down what they showed. A relative path is resolved against the directory the server starts from. A missing parent directory makes the server fail at start with `unable to open database file`.
      - Replaced the stale "a SQLite repository comes in a later story" in the intro and the "builds the service around an `InMemoryTodoRepository`" text in *Running it*.
      - Reworded the PATCH note about two writes, which was true only for memory. With SQLite a failure between the two writes can leave the rename applied without the `done` change.
    - `README.md`: *Getting started* now shows `TODO_DB=todo.db uv run uvicorn ...`, and also the in-memory start without it. *Where to look next* mentions storage and the two repositories.
    - `docs/project-guide.md`: updated the "built so far" line, the `app.repository` row (now `sqlite.py`, with SQLAlchemy Core) and the `main` module row.
      - Added two sections. *SQLite repository* covers the table, the fixed-width `created_at` format and why it is used (the database sorts `list_all()` itself), and the error mapping. *Choosing the repository* covers `build_repository`.
      - *Adding a repository* gets a third step: teach `build_repository` when to choose the new repository.

    Ran: the README's `TODO_DB=todo.db` uvicorn start from a temporary directory. It created the todo and `todo.db`. I also ran the restart persistence and the relative-path and missing-directory cases through `app.api.main`.

    Cross-read and found current: `docs/api.md` (endpoints, title and PATCH rules, errors, examples), the domain, protocol, in-memory and service sections of `docs/project-guide.md`, the `README.md` build section, and `docs/openapi.json`. The code did not change a route or a schema.

    Stale text I saw and did not touch: none that is unrelated to this story.

    Things I left in place that the reader might ask about:
    - The coder's notes in the journal (`select(_todos)` gives an untyped row, and each `from_path` never disposes its engine). The second is now in the project guide. The first is a typing detail, not for the reader of the docs.

    `check`: check: green
16. factory: started smoke-test as opencode-demo.
