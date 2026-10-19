# The guides name the operations and what a health check can tell

<!-- proposed by feature acceptance of 2026-10-19; refine before starting -->

## Description

Two sentences in the documentation still describe the project as it was before this feature, or leave the operator to put two sections together. First, `docs/project-guide.md` opens with "Built so far: the domain layer, two repositories (in memory and SQLite), the service layer and the HTTP API with its choice of storage". It does not name `/health`, `/stats` or `python -m app --version`, although the guide describes all three further down. Second, `docs/api.md` *Health* says the endpoint "answers 200 also when the database cannot be read". That is true once the server runs. But *Storage* says that a SQLite file that cannot be opened stops the server at start, so a monitor then gets no answer at all, not a 200. An operator who reads only *Health* cannot tell this. This story brings the guide's opening line up to date, and adds one sentence to *Health* that says what a monitor sees in each case. No code and no test changes. The README's intro ("being built story by story") is left to F0001-S0008, which already covers it.

## Interface

No production code, no tests.

- `docs/project-guide.md`: the opening "Built so far" line names the operations: `GET /health`, `GET /stats` and the `python -m app --version` command.
- `docs/api.md`, *Health*: one sentence says that `/health` answers only once the server has started. If `TODO_DB` names a file that cannot be opened, the server does not start (see *Storage*), and a monitor gets no connection instead of a 200.

## Acceptance criteria

1. `docs/project-guide.md`'s "Built so far" line names `/health`, `/stats` and `python -m app --version`, and nothing in it contradicts the rest of the guide.
2. `docs/api.md`'s *Health* section says that a SQLite file that cannot be opened at start keeps the server from starting, so `/health` gives no answer rather than a 200, and it points to *Storage*.
3. `make check` stays green.
4. docs: the documenter writes criteria 1 and 2 in `docs/project-guide.md` and `docs/api.md`. Before writing, the documenter checks the new *Health* sentence against the code: `TODO_DB` set to a path in a directory that does not exist makes `build_app` raise `unable to open database file`.

## Smoke test

```bash
grep -c -e '/health' -e '/stats' -e 'python -m app --version' <(grep -m1 '^Built so far' docs/project-guide.md)
```

Expect: one line, `1`.

```bash
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
TODO_DB="$d/missing/todo.db" uv run python -c "from app.api.main import app" 2>&1 | grep '^sqlalchemy.exc.OperationalError'
```

Expect: one line, `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file`. This is the failed start that the new *Health* sentence describes.

## Journal
