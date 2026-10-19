# Todo service

## Goal

A single-user to-do service that one person runs for themselves: a pure domain model, a service layer that owns the use cases, an HTTP API, and storage that is either in memory (for trying it out) or a SQLite file (for keeping the todos). Done when a todo can be created, listed, filtered by its done flag, renamed, completed, reopened and deleted over HTTP, and survives a restart when a database file is configured.

## Scope

- The `Todo` entity, its title rule and its timestamps; the domain errors; the repository protocol
- An in-memory repository and a SQLite repository behind the same protocol, proven equal by one contract test suite
- The service layer: create, get, list with a done filter, rename, complete, reopen, delete
- The HTTP API: JSON over FastAPI, one error shape, the OpenAPI schema committed as `docs/openapi.json`
- The persistence switch: a database path from the environment, memory without one

## Out of scope

- Authentication, several users, sharing
- A web front end
- Search, due dates, priorities, tags, ordering other than creation order
- Operations endpoints (health, version, statistics): feature F0002

## Stories

The order is the story numbers; start one at a time, the next when the one before is archived in `done/`.

- S0001: Domain model and in-memory repository
- S0002: Service layer with filtering
- S0003: HTTP API
- S0004: SQLite repository and persistence switch

## Decisions taken for the human

Product decisions taken while writing the stories or answering the pipeline's questions, for the human to review in one place. Each names where it was taken.

1. A title is stripped of surrounding whitespace and must then be 1 to 200 characters. (S0001, story text)
2. Timestamps are stored and returned in UTC; a `created_at` with another offset is converted, a naive one is a programming error. (S0001, story text)
3. The two title errors read `title must not be blank` and `title must be at most 200 characters`; the API returns them verbatim. (S0001, story text)
4. Lists are always in creation order (oldest first), ties broken by id; there is no other sort. (S0001, story text)
5. Completing a completed todo and reopening an open one are not errors; they return the todo as it is. (S0002, story text)
6. Every error response has the body `{"detail": "<one sentence>"}`, including request validation errors, which FastAPI would otherwise return as a list. (S0003, story text)
7. `PATCH` takes `title` and/or `done`; a body that sets neither is a 422, not a no-op. (S0003, story text)
8. The database is chosen by the environment variable `TODO_DB` (a file path); unset or empty means memory. (S0004, story text)
9. The FastAPI dependency that hands every router the service lives in `app/api/dependencies.py` from the first API story on, so later routers never import from the todo routes module. (S0003, story text)
10. The API's name in the schema and on `/docs` is `Todo service`, not the repository's name. (S0003, story text)
11. `docs/openapi.json` is written by the coder with `make openapi`, so the coder's write paths in `factory/pipeline.yml` hold that one file beside `src/*`; the rest of `docs/` stays the documenter's. (S0003, pipeline definition)
12. In a `PATCH` body a field sent as `null` counts as not set: `{}`, `{"title": null}`, `{"done": null}` and `{"title": null, "done": null}` are each a 422. A body with both fields valid applies both, the title first. (S0003, story text; the shakedown's intake question on demo #4, 2026-10-18)
13. Test helpers, constants and fixtures that more than one test module needs live once, in a module at the `tests/` root or in `tests/conftest.py`; the standing leave in `CLAUDE.md` lets the tester move one there and change the earlier tests that held it, keeping what each checks. (`CLAUDE.md`; the shakedown's decision 13, the human's answer on demo #4)
14. The SQLite table `todos` stores `id` as the UUID's hyphenated text, `created_at` as ISO 8601 text in UTC (offset `+00:00`) and `done` as a boolean; a test reads a row back with a Core `select` to hold it. (S0004, story text; the shakedown's decision 15)
15. No repository inherits the `TodoRepository` protocol; one parametrized test in `tests/repository/test_contract.py` holds it, a row for each repository class, and a later repository adds its row there. (S0001 and S0004, story text; the shakedown's decision 16)
16. `SqliteTodoRepository.from_path` takes a `str` or a `Path`, both tested. (S0004, story text; the shakedown's intake question on demo #5)
17. `list(done=None)` is no filter, as `list()` is. (S0002, story text)
18. `POST /todos` strips the title first and then applies the domain's length and blank rules; the request schema puts no rule of its own on `title`: `"  Buy milk "` is created as `Buy milk`, and 200 characters with surrounding spaces are accepted. (S0003, the human's answer on demo #3)
