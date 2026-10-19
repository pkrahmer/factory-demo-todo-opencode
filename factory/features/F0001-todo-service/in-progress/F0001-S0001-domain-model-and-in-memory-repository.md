---
stage: doing
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 1
comments_read: []
handed_over: null
claim: null
journal:
- number: 1
  speaker: human
  kind: created
  at: '2026-10-19T12:44:07.136469Z'
  stage: intake
- number: 2
  speaker: factory
  kind: started
  at: '2026-10-19T12:44:07.150760Z'
  stage: intake
- number: 3
  speaker: intake
  kind: result
  at: '2026-10-19T12:44:34.306199Z'
  stage: intake
  run: ac53c480166942b88ebb3851974476ac
- number: 4
  speaker: factory
  kind: started
  at: '2026-10-19T12:44:54.661724Z'
  stage: tests
- number: 5
  speaker: tester
  kind: result
  at: '2026-10-19T12:46:36.144058Z'
  stage: tests
  run: c6fe28f8d77741858a4082e8c6b6a5b5
---

# Domain model and in-memory repository

## Description

Create the domain layer of the to-do service: the `Todo` entity with its title rule and UTC timestamps, the domain errors, and the repository protocol; and the first repository behind that protocol, in memory, so that the service layer can be built and tested against it next. No service, no API, no SQLite yet.

## Interface

`src/app/domain/model.py`

```python
MAX_TITLE_LENGTH = 200

@dataclass(frozen=True, slots=True)
class Todo:
    id: UUID
    title: str
    done: bool
    created_at: datetime

    @classmethod
    def new(cls, title: str, *, now: datetime) -> "Todo": ...
    def with_title(self, title: str) -> "Todo": ...
    def with_done(self, done: bool) -> "Todo": ...
```

The rules hold however a todo is built (the constructor, `new`, `with_title`, `with_done`); each has a criterion below:

- the title is stripped of surrounding whitespace, then must be 1 to `MAX_TITLE_LENGTH` characters, else `InvalidTitle`;
- `created_at` must be timezone-aware and is converted to UTC; a naive one raises `ValueError`;
- `new` gives a fresh `uuid4` id and `done=False`;
- `with_title` and `with_done` return a new todo and leave the original as it was.

`src/app/domain/errors.py`

```python
class TodoError(Exception): ...

class InvalidTitle(TodoError): ...

class TodoNotFound(TodoError):
    todo_id: UUID
    def __init__(self, todo_id: UUID) -> None: ...

class DuplicateTodo(TodoError):
    todo_id: UUID
    def __init__(self, todo_id: UUID) -> None: ...
```

`src/app/domain/repository.py`

```python
class TodoRepository(Protocol):
    def add(self, todo: Todo) -> None: ...
    def get(self, todo_id: UUID) -> Todo: ...
    def list_all(self) -> list[Todo]: ...
    def update(self, todo: Todo) -> None: ...
    def delete(self, todo_id: UUID) -> None: ...
```

`src/app/repository/memory.py`

```python
class InMemoryTodoRepository:   # satisfies TodoRepository structurally, no inheritance
    def __init__(self) -> None: ...
```

Tests: `tests/domain/test_model.py`, `tests/domain/test_errors.py`, `tests/domain/test_imports.py`, and the repository behaviour as one contract suite in `tests/repository/test_contract.py`, run through a `repository` fixture that is parametrized over a module-level list of repository factories, each a `Callable[[Path], TodoRepository]` that the fixture calls with the test's `tmp_path`; here the list holds one factory, which returns `InMemoryTodoRepository()`. A later repository, also one that keeps a file under `tmp_path`, joins the suite by adding its factory to that list and its class to a second module-level list, of repository classes, with no other change to the file but a move of a shared test helper under the standing leave of `CLAUDE.md`. Fixed ids are built with `UUID(int=n)`.

## Acceptance criteria

1. `Todo.new("Buy milk", now=t)` with a timezone-aware `t` returns a todo titled `"Buy milk"`, not done, with `created_at == t` and an id whose UUID version is 4.
2. Two calls of `Todo.new` with the same arguments return todos with different ids.
3. The title is stripped of surrounding whitespace, whether the todo comes from `Todo(...)`, `Todo.new` or `with_title`: `"  Buy milk \n"` becomes `"Buy milk"`. Three rows of one parametrized test.
4. An empty or whitespace-only title (`""`, `"   "`, `"\n\t"`) raises `InvalidTitle` whose message is `title must not be blank`, from `Todo(...)`, `Todo.new` and `with_title` alike.
5. The length rule on both sides, as rows of one parametrized test, from `Todo(...)`, `Todo.new` and `with_title` alike: a title of 1 character and one of exactly 200 characters are accepted, also when surrounded by whitespace; a title of 201 characters after stripping raises `InvalidTitle` whose message is `title must be at most 200 characters`.
6. A `created_at` with a non-UTC offset is converted to UTC: `datetime(2026, 10, 4, 14, 0, tzinfo=timezone(timedelta(hours=2)))` is stored as a datetime equal to it whose `utcoffset()` is zero, from `Todo(...)` and `Todo.new` alike.
7. A naive `created_at` (no `tzinfo`) raises `ValueError`, not `InvalidTitle`, from `Todo(...)` and `Todo.new` alike.
8. `with_title` returns a new todo with the new title and the same id, done flag and `created_at`; the original keeps its title.
9. `with_done` returns a new todo with the new done flag and the same id, title and `created_at`; the original keeps its done flag.
10. Assigning to a field of a todo raises `dataclasses.FrozenInstanceError` (`setattr` with the field's name in a variable).
11. `TodoNotFound(todo_id)` carries the id as `todo_id`, and its message is `todo <todo_id> not found`, the UUID in its hyphenated form.
12. `DuplicateTodo(todo_id)` carries the id as `todo_id`, and its message is `todo <todo_id> already exists`.
13. `InvalidTitle`, `TodoNotFound` and `DuplicateTodo` are subclasses of `TodoError`.
14. `add` then `get` returns a todo equal to the one added.
15. `add` with an id that is already stored raises `DuplicateTodo` carrying that id, and `get` still returns the todo stored first.
16. `get`, `update` and `delete` with an unknown id each raise `TodoNotFound` carrying that id (three rows of one parametrized test); after the failed `update`, `list_all()` is still empty.
17. `list_all` on an empty repository returns `[]`.
18. `list_all` returns the todos ordered by `created_at`, oldest first, whatever order they were added in.
19. Todos with equal `created_at` are ordered by id ascending (ids built with `UUID(int=n)` make it observable).
20. `update` replaces the stored todo that has the same id; `get` afterwards returns the new version.
21. `delete` removes the todo; `get` afterwards raises `TodoNotFound`.
22. No repository class inherits the protocol: `InMemoryTodoRepository` is not a subclass of `TodoRepository` (`TodoRepository` is not in its `__mro__`; `issubclass` refuses a protocol that is not `runtime_checkable`), as a row of one parametrized test in `tests/repository/test_contract.py` over the module-level list of repository classes (here one class); and the contract suite's `repository` fixture is annotated as returning `TodoRepository`, so `make check` (mypy) proves each repository satisfies the protocol.
23. No module in `app.domain` imports `fastapi`, `pydantic`, `sqlalchemy`, or an `app` module outside `app.domain` (a test that parses the imports of every module under `src/app/domain` and names only these forbidden ones).
24. `make check` stays green.
25. docs: `docs/project-guide.md` explains the layers (which may import which, and that service and repository never import each other) and the domain model (the `Todo` fields, the title rule, UTC timestamps, the three errors, the repository protocol and its ordering); the README's *Where to look next* links it.

## Smoke test

```bash
uv run python -c "
from datetime import UTC, datetime, timedelta
from app.domain.model import Todo
from app.repository.memory import InMemoryTodoRepository
repo = InMemoryTodoRepository()
t0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
a = Todo.new('  Buy milk ', now=t0)
b = Todo.new('Write the next story', now=t0 + timedelta(minutes=1))
repo.add(b); repo.add(a)
repo.update(a.with_done(True))
for t in repo.list_all(): print(t.done, repr(t.title), t.created_at.isoformat())
"
```

Expect: two lines, `True 'Buy milk' 2026-10-04T12:00:00+00:00` then `False 'Write the next story' 2026-10-04T12:01:00+00:00`: creation order although `b` was added first, the title stripped.

```bash
uv run python -c "
from datetime import UTC, datetime
from app.domain.errors import InvalidTitle
from app.domain.model import Todo
for title in ('   ', 'x' * 201):
    try:
        Todo.new(title, now=datetime.now(UTC))
    except InvalidTitle as e:
        print(type(e).__name__, '-', e)
"
```

Expect: two lines, `InvalidTitle - title must not be blank`, then `InvalidTitle - title must be at most 200 characters`.

## Journal

1. 2026-10-19 human: created.
2. factory: started intake as opencode-demo.
3. intake: accepted

   - Interface: it names concrete modules and signatures: `app/domain/model.py` (`Todo`, `MAX_TITLE_LENGTH`, `new`, `with_title`, `with_done`), `errors.py`, `repository.py` (`TodoRepository`) and `app/repository/memory.py` (`InMemoryTodoRepository`). The test modules and the contract-suite mechanism are also named: a `repository` fixture over a list of factories, plus a list of classes. Each Interface comment has a criterion:
     - Title strip: 3.
     - Title bounds: 4 and 5.
     - UTC conversion: 6.
     - Naive datetime raising `ValueError`: 7.
     - `new` giving a uuid4 and `done=False`: 1 and 2.
     - `with_*` leaving the original unchanged: 8 and 9.
     - Frozen dataclass: 10.
     - "However a todo is built": the criteria name `Todo(...)`, `Todo.new` and `with_title` explicitly.
   - Criteria: each fits one parametrized or plain test with no further decision, and each rule has its failing side:
     - Blank title: 4.
     - 201 characters: 5, with 1 and 200 accepted.
     - Naive datetime: 7.
     - Duplicate id: 15.
     - Unknown id for get, update and delete: 16, plus the repository left unchanged after a failed update.
     - The repository ordering has both clauses: `created_at` in 18, id tie-break in 19.
     - Error messages: 11 and 12.
     - Error hierarchy: 13.
     - Empty list: 17.
     - No inheritance of the protocol: 22.
     - Domain import ban: 23.
     - Closing criteria: `make check` and docs are last (24, 25).
   - Smoke test: both blocks are runnable `uv run python -c` commands against the stated modules. Each `Expect:` gives exact output lines (creation order despite insertion order, stripped title, UTC isoformat, and the two exact error messages).
   - Architecture: it matches `CLAUDE.md`.
     - The domain holds the frozen dataclass, the errors and the protocol, and imports only the standard library.
     - The in-memory repository sits in `app.repository` and satisfies the protocol structurally.
     - There is no service or API code.
     - The existing import-linter layers contract already covers these layers.
     - `docs/project-guide.md` does not exist yet; criterion 25 has the documenter create it. The README already has a *Where to look next* section to extend.
   - Scope: it stays inside feature scope (entity, title rule, timestamps, errors, protocol, in-memory repository). It stays out of the SQLite repository (S0004), the service (S0002) and the API (S0003). It changes no other story's tests. It is consistent with feature decisions 1–4 and 15.
4. factory: started tests as opencode-demo.
5. tester: I wrote red tests for criteria 1–23 against the Interface; `make lint` is green, and I skipped the type check as the stage says. One run of `make test` ended with `1 failed, 3 errors`: three test modules could not be imported, and the import check fails because `src/app/domain` has no modules yet. No criterion needed interpreting.

   Criterion → test:
   - criterion 1: tests/domain/test_model.py::test_new_gives_an_open_todo_with_a_uuid4_id
   - criterion 2: tests/domain/test_model.py::test_new_gives_a_fresh_id_on_every_call
   - criterion 3: tests/domain/test_model.py::test_title_is_stripped_of_surrounding_whitespace (rows: constructor, new, with_title)
   - criterion 4: tests/domain/test_model.py::test_blank_title_is_rejected (`""`, `"   "`, `"\n\t"` × the three ways of building)
   - criterion 5: tests/domain/test_model.py::test_title_length_is_limited_to_200_characters (1, 200, both with whitespace around them, and 201 × the three ways of building)
   - criterion 6: tests/domain/test_model.py::test_created_at_is_converted_to_utc (constructor, new)
   - criterion 7: tests/domain/test_model.py::test_naive_created_at_is_rejected_with_value_error (constructor, new)
   - criterion 8: tests/domain/test_model.py::test_with_title_returns_a_new_todo_and_keeps_the_original
   - criterion 9: tests/domain/test_model.py::test_with_done_returns_a_new_todo_and_keeps_the_original
   - criterion 10: tests/domain/test_model.py::test_todo_fields_cannot_be_assigned (one row per field)
   - criterion 11: tests/domain/test_errors.py::test_todo_not_found_carries_the_id_and_names_it
   - criterion 12: tests/domain/test_errors.py::test_duplicate_todo_carries_the_id_and_names_it
   - criterion 13: tests/domain/test_errors.py::test_domain_errors_share_the_todo_error_base
   - criterion 14: tests/repository/test_contract.py::test_added_todo_can_be_read_back
   - criterion 15: tests/repository/test_contract.py::test_adding_a_stored_id_is_rejected
   - criterion 16: tests/repository/test_contract.py::test_unknown_id_is_not_found (rows: get, update, delete; each row checks that `list_all()` is still `[]`)
   - criterion 17: tests/repository/test_contract.py::test_empty_repository_lists_nothing
   - criterion 18: tests/repository/test_contract.py::test_todos_are_listed_oldest_first
   - criterion 19: tests/repository/test_contract.py::test_todos_created_at_the_same_time_are_listed_by_id
   - criterion 20: tests/repository/test_contract.py::test_update_replaces_the_stored_todo
   - criterion 21: tests/repository/test_contract.py::test_deleted_todo_is_gone
   - criterion 22: tests/repository/test_contract.py::test_repository_does_not_inherit_the_protocol (one row per entry in the module-level `REPOSITORY_CLASSES`). The `repository` fixture is parametrized over `REPOSITORY_FACTORIES` (`Callable[[Path], TodoRepository]`, called with `tmp_path`) and annotated `-> TodoRepository`, so mypy checks that each repository satisfies the protocol.
   - criterion 23: tests/domain/test_imports.py::test_domain_imports_no_framework_and_no_outer_layer. It parses every module under `src/app/domain` with `ast`, works out relative imports, and names only the banned imports: fastapi, pydantic, sqlalchemy, and any `app` module outside `app.domain`. It also fails when the folder has no modules.
   - criteria 24 and 25 are the closing `make check` and docs criteria; they have no tests.

   Files created: tests/domain/__init__.py, tests/domain/test_model.py, tests/domain/test_errors.py, tests/domain/test_imports.py, tests/repository/__init__.py, tests/repository/test_contract.py. I changed no earlier test file.

   Modules the test run could not import: app.domain.errors, app.domain.model, app.domain.repository, app.repository.memory.

   `lint`: lint: green (0.0 s)
   `test`: 1 failed, 3 errors in 1.74s
