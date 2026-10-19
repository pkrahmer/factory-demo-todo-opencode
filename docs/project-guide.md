# Project guide

For anyone changing the to-do service: the layers, why they are drawn that way, and the domain model. `CLAUDE.md` holds the rules every change follows; this file explains what they protect.

Built so far: the domain layer, an in-memory repository and the service layer. The API and the SQLite repository come in later stories.

## Layers

One package, `app`, under `src/`:

| Package | Holds | May import |
| --- | --- | --- |
| `app.api` | HTTP to service calls; the one place where domain errors become status codes; wiring (choosing the concrete repository) in `app.api.main` | `app.service`, `app.domain` |
| `app.service` | The use cases, written against the repository protocol | `app.domain` |
| `app.repository` | Concrete storage, one module per kind (`memory.py` so far) | `app.domain` |
| `app.domain` | The entity, the errors, the repository protocol | the standard library and itself |

`app.service` and `app.repository` sit on the same level and never import each other. The service sees storage only through the protocol in `app.domain.repository`; a repository does not know there is a service. That is what lets the service be tested against the in-memory repository and run against SQLite.

`make layers` (import-linter) enforces the order for every layer that exists, including the rule that service and repository stay apart. `app.domain` goes further, and a test enforces it: no import of `fastapi`, `pydantic` or `sqlalchemy`, and none of an `app` module outside `app.domain`. The domain does no I/O.

Boundaries use Pydantic models; the core uses frozen dataclasses.

## Domain model

### Todo

`app.domain.model.Todo` is a frozen, slotted dataclass:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | `UUID` | Identity; `Todo.new` draws a random `uuid4` |
| `title` | `str` | Stripped of surrounding whitespace, 1 to `MAX_TITLE_LENGTH` (200) characters |
| `done` | `bool` | `False` for a new todo |
| `created_at` | `datetime` | Timezone-aware, always stored in UTC |

Todos are values: assigning to a field raises `dataclasses.FrozenInstanceError`. `with_title(title)` and `with_done(done)` return a changed copy and leave the original as it was. `Todo.new(title, *, now)` takes the time from its caller, so the domain never reads the clock.

The rules live in `Todo.__post_init__`, so they hold however a todo is built: the constructor, `new`, `with_title` and `with_done`. A rule has one copy and no path around it.

- **Title.** Surrounding whitespace is stripped first, then the length is checked. A blank title raises `InvalidTitle("title must not be blank")`. A title of more than 200 characters after stripping raises `InvalidTitle("title must be at most 200 characters")`. A title of exactly 200 is accepted, also with whitespace around it.
- **Timestamps.** `created_at` with a non-UTC offset is converted to UTC; the result equals the input and its `utcoffset()` is zero. A naive `created_at` raises `ValueError`, not `InvalidTitle`.

### Errors

All in `app.domain.errors`, all subclasses of `TodoError`:

| Error | Raised when | Carries | Message |
| --- | --- | --- | --- |
| `InvalidTitle` | the title rule fails | | as above |
| `TodoNotFound` | an id is not stored | `todo_id` | `todo <id> not found` |
| `DuplicateTodo` | an id is already stored | `todo_id` | `todo <id> already exists` |

The id appears in its hyphenated form. The API layer maps these to status codes; the domain does not know about HTTP.

### Repository protocol

`app.domain.repository.TodoRepository` is a `typing.Protocol`:

| Method | Behaviour |
| --- | --- |
| `add(todo)` | Stores a new todo; raises `DuplicateTodo` if the id is stored, and the todo stored first is kept |
| `get(todo_id)` | Returns the todo; raises `TodoNotFound` |
| `list_all()` | Returns every todo, oldest `created_at` first; equal times are ordered by id ascending; `[]` when empty |
| `update(todo)` | Replaces the stored todo with the same id; raises `TodoNotFound` and changes nothing if there is none |
| `delete(todo_id)` | Removes the todo; raises `TodoNotFound` |

A repository satisfies the protocol structurally and does not inherit it; a test checks that no repository class has `TodoRepository` in its `__mro__`. The `repository` fixture in `tests/repository/test_contract.py` is typed `-> TodoRepository`, so `mypy --strict` checks that each repository fits.

### In-memory repository

`app.repository.memory.InMemoryTodoRepository` keeps todos in a dictionary by id, for as long as the process runs. It sorts on `(created_at, id)` when listing.

## Service

`app.service.todo_service.TodoService` holds the use cases. It is built with a `TodoRepository` and a clock: `TodoService(repository, clock=utc_now)`. It imports only `app.domain` and the standard library; it reaches storage through the repository protocol and never imports `app.repository`, so any repository that satisfies the protocol works.

| Method | Behaviour |
| --- | --- |
| `create(title)` | Builds a new open todo stamped with the clock, stores it and returns it; raises `InvalidTitle` before anything is stored |
| `get(todo_id)` | Returns the todo; raises `TodoNotFound` |
| `list(*, done=None)` | Returns the todos in the repository's order (creation order); `done=True` keeps the completed ones, `done=False` the open ones, `None` all |
| `rename(todo_id, title)` | Returns the todo with the new title (stripped); id, done flag and `created_at` stay; raises `InvalidTitle` or `TodoNotFound`, and the stored todo is unchanged |
| `complete(todo_id)` | Returns the todo with `done` true; completing a completed todo is not an error |
| `reopen(todo_id)` | Returns the todo with `done` false; reopening an open todo is not an error |
| `delete(todo_id)` | Removes the todo; raises `TodoNotFound` |

What the service owns:

- **The use cases.** Each one reads, changes through `Todo.with_title` or `Todo.with_done`, and writes back with `update`. The rules stay in the domain: the service has no title check of its own, and `InvalidTitle` and `TodoNotFound` reach the caller unchanged.
- **The clock.** `Clock` is `Callable[[], datetime]`. `utc_now()` returns `datetime.now(UTC)` and is the default. The service reads the clock only in `create`; tests pass a fixed or a ticking clock so that times and order are observable.
- **The done filter.** The repository protocol has no filtered list. The service takes `list_all()` and keeps the todos whose `done` flag matches, so the order is the repository's. A filter on another field, or one that the database should apply, means extending the protocol.

## Adding a repository

1. Write the class in `app/repository/`, with no base class, importing only `app.domain`.
2. In `tests/repository/test_contract.py`, add its factory (a `Callable[[Path], TodoRepository]`, called with the test's `tmp_path`) to `REPOSITORY_FACTORIES` and its class to `REPOSITORY_CLASSES`. The contract suite then runs against it.

## Try it

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

Prints `True 'Buy milk' 2026-10-04T12:00:00+00:00`, then `False 'Write the next story' 2026-10-04T12:01:00+00:00`: creation order although `b` was added first, the title stripped.

The same through the service, which stamps the time itself:

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

Prints `['Buy milk']`, then `['Write the next story']`, then `Write story S0003 2026-10-04T12:00:00+00:00`.
