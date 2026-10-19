---
stage: tests
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 4
comments_read: []
handed_over: null
claim:
  instance: opencode-demo
  stage: tests
  started_at: '2026-10-19T13:13:16.622475Z'
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
