# Operations

## Goal

What running the service needs beyond its features: a health endpoint a monitor can poll, a version command for support, and statistics for a glance at the data. Done when an operator can tell from outside whether the service is up, which version runs and with which storage, and how many todos are open and done.

## Scope

- `GET /health`: status, version, storage kind
- `python -m app --version`
- `GET /stats`: open, done, total

## Out of scope

- Metrics export, logging configuration, deployment
- Authentication of the operations endpoints (the service is single-user)

## Stories

The order is the story numbers; start one at a time, the next when the one before is archived in `done/`.

- S0001: Health endpoint
- S0002: Version command
- S0003: Todo statistics

## Decisions taken for the human

Product decisions taken while writing the stories or answering the pipeline's questions, for the human to review in one place. Each names where it was taken.

1. `/health` reports `status`, the package `version` and the `storage` kind (`memory` or `sqlite`), and never touches the repository, so it answers even when the database does not. (S0001, story text)
2. The version command prints `app <version>`; any other argument prints the usage line to stderr and exits 2. (S0002, story text)
3. Statistics are three counts, `open`, `done`, `total`; `total` is derived, never stored. (S0003, story text)
4. No story of its own for a shared service dependency: `app/api/dependencies.py` exists since F0001-S0003. (feature text)
5. Only exactly `--version` prints the version; `--version` with anything after it is a usage error like any other argument. (S0002, story text)
6. An empty `TODO_DB` reports `"storage": "memory"`, as it chooses the in-memory repository (F0001 decision 8); the health story has a criterion for it. (S0001, story text; the intake question of v1's run 4, answered in advance)
7. `build_app` is tested with todos, not only through `/health`: the repository it chooses is the one the todo routes use. (S0001, story text; F0002's acceptance at the shakedown, 2026-10-18)
8. `python -m app` is tested as a child process with the interpreter that runs the tests; it is a short command, not a server, so it fits the rule that tests start no server. (S0002, story text; F0002's acceptance at the shakedown)
9. `stats` reads the repository once, with one `list_all`. (S0003, story text)
