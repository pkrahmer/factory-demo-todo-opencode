# To-do service

A single-user to-do service with an HTTP API: create todos, list and filter them, rename, complete, reopen and delete them, kept in memory or in a SQLite file. It is being built story by story; this README grows with it.

## Getting started

```bash
uv sync       # install
make check    # everything the pipeline checks: lint, types, layers, static analysis, secrets, licences, tests
```

Start the server with the todos in a SQLite file, created on first start, so that they survive a restart:

```bash
TODO_DB=todo.db uv run uvicorn app.api.main:app --port 8765
```

Without `TODO_DB` (or with it empty) the todos are kept in memory and are gone when the server stops:

```bash
uv run uvicorn app.api.main:app --port 8765
```

Open <http://localhost:8765/docs> for the interactive schema, or try it from a shell:

```bash
curl -s -X POST localhost:8765/todos -H 'content-type: application/json' -d '{"title": "Buy milk"}'
curl -s localhost:8765/todos
```

## Where to look next

- `CLAUDE.md`: the rules every change follows (architecture, tests, checks)
- `docs/api.md`: every endpoint, the title and `PATCH` rules, the error body, where the todos are stored; the schema itself is `docs/openapi.json`
- `docs/project-guide.md`: the layers and their reasons, the domain model (the `Todo` entity, its title rule, the errors, the repository protocol), the two repositories, the service (the use cases, the clock, the done filter) and the API modules

## How it is built

Built by the factory (github.com/pkrahmer/factory): features and their stories live under `factory/features/`, one folder per feature, and one stage agent at a time takes a story through tests, code, review, docs and a smoke test. A story's pull request carries the whole story; merging it accepts the story.
