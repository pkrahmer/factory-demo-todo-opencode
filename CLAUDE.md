# To-do service

A single-user to-do service (FastAPI, SQLite) built by the factory (github.com/pkrahmer/factory); the pipeline's rules reach every agent in its instructions, so this file holds only what is true of this project. `factory/` holds the pipeline definition, the story form and the features with their stories.

## Language
- Everything in this repository is English: code, comments, docs, work items, commit messages.

## Architecture
- One package, `app`, under `src/`. Layers: `app.api` → `app.service` → `app.domain`; `app.repository` → `app.domain`. Wiring (choosing the concrete repository) happens in `app.api.main` only.
- `app.domain` imports nothing from the project outside `app.domain` and no framework (`fastapi`, `pydantic`, `sqlalchemy`), and does no I/O: frozen dataclasses, the domain errors, the repository protocol.
- `app.service` depends on the repository protocol only; it never imports `app.repository` or `app.api`.
- `app.repository` implements the domain protocol structurally (no inheritance) and imports nothing from `app.service` or `app.api`.
- `app.api` translates HTTP to service calls and maps domain errors to status codes in one place.
- Boundaries use Pydantic models; the core uses frozen dataclasses. No bare dicts across function boundaries.
- Type everything; `mypy --strict` is part of the checks. `Any` only at a boundary that Pydantic validates immediately.
- import-linter (`make layers`) enforces the layer order for every layer that exists, including that `app.service` and `app.repository` never import each other; the framework-free domain is each story's criteria and tests.
- Before changing the architecture, read `docs/project-guide.md` when it exists; lasting reasons are in `docs/decisions.md`.
- Before writing a helper, search `src/app` and `tests/` for one that does the same, and reuse or extend it; the reviewer counts a second copy of an existing helper as a finding.

## Tests
- pytest. Tests live under `tests/`, mirroring the layer (`tests/domain/`, `tests/service/`, `tests/api/`, `tests/repository/`), each folder a package with an `__init__.py`; a module outside the layers is tested at the `tests/` root.
- Plain test functions, shared fixtures in `tests/conftest.py`, parametrize for tables of cases. Fake the repository through its protocol, or use the in-memory repository once it exists; never mock the code under test.
- No network, no sleeps, no files outside `tmp_path`. HTTP is tested through FastAPI's `TestClient` (httpx) against `create_app`; no server process in tests.
- Every limit the Interface states is tested on both sides, also when no criterion spells out the refused side (a title of 200 characters and one of 201; an empty text and one of one character). The sides of one rule are rows of one parametrized test, not separate test functions; setup that several tests share is a fixture.
- Test data obeys the code already built, unless the test is about that rule: a title the domain accepts, a todo that exists before it is read, a time with a time zone.
- A test that reads the source (the imports of a layer) names what a module must not import, never a list of what it may: `make mutants` runs the tests on mutmut's rewritten copy, which adds imports of its own.
- Tests pass `mypy --strict` once the code exists: never use the value of a call to a function typed `-> None` (no `assert f() is None`); call it as a statement. A fixture's `request.param` is `Any`: assign it to a variable of its type before you return or call it (`factory: Callable[[Path], TodoRepository] = request.param`), since returning it from a fixture typed `-> TodoRepository` fails mypy's `no-any-return`, and the tests stage does not run the type check.
- To test that a Pydantic model refuses an unknown or a wrong-typed field, construct it through a variable typed `type[BaseModel]`; assign to a field of a frozen model or a frozen dataclass with `setattr(instance, field, value)`, the field's name in a variable; call an abstract class through a variable typed `type[object]`. None of these needs a `type: ignore`.
- Fake commit ids and other hexadecimal test values are low-entropy (`"a" * 40`), so that `make secrets` stays green without a baseline entry. Fixed ids are built with `UUID(int=n)`.
- A test that waits for a time limit gives the process it starts room to start: the tests may run on every core at once, so a child can need more than a second before it does anything. Give it a limit of a few seconds and an upper bound on the elapsed time with room above it; never check that a one-second limit is met to the tenth.
- The standing leave to move a shared test helper: a helper, constant or fixture that a new test would copy from another story's test module, or that an earlier test module still holds as a copy of a shared one, may be moved to one shared place under `tests/` (a module at its root such as `tests/fakes.py`, or `tests/conftest.py` for a fixture), and the earlier tests that held it changed to use it from there, without asking, as long as every earlier test keeps its name and checks the same thing. The tester makes the move, never the coder, and its entry names each earlier test file it changed. Any other change to a test another story wrote still needs the human's leave.

## Docs
- `README.md` is for the newcomer: what it is, how to run it, where to look next. `docs/project-guide.md` is the guide for agents: the layers and their reasons, the domain model, the service. `docs/api.md` holds what the schema cannot say (title rules, error shape, filters, storage, the operations endpoints). `docs/decisions.md` is the decision log. The documenter stage keeps them true from each story's docs criterion; the coder does not write them.
- `docs/openapi.json` is generated: `make openapi` writes it from `app.api.main:app`, a test fails when it is stale, and the coder runs the target after changing a route or a schema (it is in the coder's write paths). Nobody edits it by hand.
- Docstrings: one per module (its purpose, a sentence) and one per public class and function in `app.domain` and `app.service`, which are the interface; `app.api`, `app.repository` and `__main__` need only the module docstring. None on private names or where the signature says it all. Comments say why, never what. `ruff`'s `D` rules (Google convention) enforce the presence; the reviewer judges the content.

## Checks
- `make check` must be green before any stage reports done. It runs `make lint` (ruff check and format check), `make types` (`mypy --strict`), `make layers` (`uv run lint-imports`), `make sast` (semgrep with the rules in `security/semgrep`, and bandit over `src/app`), `make secrets` (detect-secrets against `.secrets.baseline`, over the files changed against `origin/main`, every tracked file on `main` itself), `make licenses` (pip-licenses against an allow list for the production dependencies) and `make test` (pytest on every core with pytest-xdist, coverage as `pyproject.toml` sets it, a JUnit report in `.reports/junit.xml`). Each target ends with the line `<target>: green (<seconds> s)`; `make check` ends with `check: green`.
- `make lint` and `make test` run those two alone. `make duplicates` writes similar code (pylint's duplicate-code) and dead code (vulture) in `src/app` to `.reports/` and counts them on its last line: a report, never a check. `make mutants FEATURE=<feature id>` runs mutmut over the modules of `src/app` that the feature's story commits on `origin/main` changed (`work item <id>: ...`, or the pull request's title `<id>: ...` after a squash merge), and lists the surviving mutants: run by the feature acceptance, never part of `make check`; mutmut rewrites the source with its own import, so a test that reads the source names only what a module must not import (see *Tests*), and a test that cannot hold on the rewritten copy is left out of its runs with a `--deselect` in `pytest_add_cli_args` of `[tool.mutmut]` in `pyproject.toml` (a question for the human, since the file is theirs). The pipeline definition names `check`, `lint`, `test` and `duplicates`, a report of the stage `doing`.
- Run `make check` and every other make target in the foreground and read its output; never start one in the background, and never wait for one with `pgrep -f`. Give `make check` the shell tool's largest timeout (600000 ms), so that the tool does not move it to the background.
- Run Python through `uv run`. The dependencies of the whole to-do service are already in `pyproject.toml`, pinned: FastAPI, Pydantic, SQLAlchemy (Core), uvicorn; httpx for the test client.

## Not without asking (end the stage with `question`)
- New dependency, new top-level package, change to `factory/`, change to a test you did not write beyond the standing leave under *Tests*, a new entry in `.secrets.baseline` or a `pragma: allowlist secret`, a `nosemgrep` or `nosec` marker, a licence outside the allow list.
- A story that changes a test another story wrote beyond the standing leave names that test in its Interface; that is the human's leave, and the tester makes the change, never the coder.
