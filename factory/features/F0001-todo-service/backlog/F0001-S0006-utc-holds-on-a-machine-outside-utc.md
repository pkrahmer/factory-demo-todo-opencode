# UTC conversion holds on a machine whose local time is not UTC

<!-- proposed by feature acceptance of 2026-10-19; refine before starting -->

## Description

Feature decision 2 says timestamps are stored and returned in UTC. The tests check this only on a machine whose local time zone is UTC, as the factory's machine is. The mutation run shows that `astimezone(UTC)` replaced by `astimezone(None)` (the machine's local zone) goes unnoticed in two places: `app.domain.model._in_utc` and `app.repository.sqlite._stored_created_at`. On a laptop in Berlin, that mutant would store local times. The SQLite format would then label them `+00:00` and shift every todo by the zone's offset. The mutation run also shows that the message of the `ValueError` for a naive `created_at` is not held by any test. This story adds the tests that hold both rules on a machine in another zone, and fixes the message. The code is expected to pass unchanged. Nothing else changes.

## Interface

No production signature changes. The rules held:

- `Todo(...)` and `Todo.new` convert `created_at` to UTC whatever the process's local time zone is.
- `SqliteTodoRepository` stores `created_at` in UTC and reads back an equal time whatever the process's local time zone is.
- A naive `created_at` raises `ValueError` with the message `created_at must be timezone-aware`.

`tests/conftest.py` gains a fixture `local_zone_not_utc`. It sets the environment variable `TZ` to `America/New_York` with `monkeypatch.setenv`, calls `time.tzset()`, and restores both after the test (`time.tzset()` again after monkeypatch undoes `TZ`). Tests: `tests/domain/test_model.py` gets new rows or a new test, and so does `tests/repository/test_sqlite.py`. Both files are earlier stories' tests, so the human's leave is needed to add to them; or the new tests go into new modules `tests/domain/test_local_zone.py` and `tests/repository/test_sqlite_local_zone.py`, which needs no leave. The human chooses at refinement; the second is the default.

## Acceptance criteria

1. With `local_zone_not_utc` active, `Todo(...)` and `Todo.new` (two rows of one parametrized test) with `created_at = datetime(2026, 10, 4, 14, 0, tzinfo=timezone(timedelta(hours=2)))` give a `created_at` equal to it whose `utcoffset()` is `timedelta(0)`.
2. With `local_zone_not_utc` active, a todo created at `datetime(2026, 10, 4, 12, 0, tzinfo=UTC)` and added to a `SqliteTodoRepository` on a file under `tmp_path` has a stored `created_at` column (read with a Core `select`) of exactly `2026-10-04T12:00:00.000000+00:00`, and `get` returns it equal to the original.
3. A naive `created_at`, from `Todo(...)` and `Todo.new` alike (two rows of one parametrized test), raises `ValueError` whose message is exactly `created_at must be timezone-aware`.
4. The fixture leaves no trace: a test that runs after one using `local_zone_not_utc` in the same process sees `time.localtime()` with the zone it had before (checked inside the fixture's teardown by comparing `time.tzname` before and after).
5. `make check` stays green.
6. docs: `docs/project-guide.md`, *Timestamps*: the naive-time message `created_at must be timezone-aware`, and that the conversion does not depend on the machine's local zone.

## Smoke test

```bash
TZ=America/New_York uv run python -c "
from datetime import datetime, timedelta, timezone
from app.domain.model import Todo
t = Todo.new('Buy milk', now=datetime(2026, 10, 4, 14, 0, tzinfo=timezone(timedelta(hours=2))))
print(t.created_at.isoformat())
try:
    Todo.new('Buy milk', now=datetime(2026, 10, 4, 14, 0))
except ValueError as e:
    print(e)
"
```

Expect: two lines, `2026-10-04T12:00:00+00:00`, then `created_at must be timezone-aware`.

```bash
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
TZ=America/New_York uv run python -c "
import sys
from datetime import UTC, datetime
from app.domain.model import Todo
from app.repository.sqlite import SqliteTodoRepository
repo = SqliteTodoRepository.from_path(sys.argv[1])
t = Todo.new('Buy milk', now=datetime(2026, 10, 4, 12, 0, tzinfo=UTC))
repo.add(t)
print(SqliteTodoRepository.from_path(sys.argv[1]).get(t.id).created_at.isoformat())
" "$d/todo.db"
```

Expect: one line, `2026-10-04T12:00:00+00:00`.

## Journal
