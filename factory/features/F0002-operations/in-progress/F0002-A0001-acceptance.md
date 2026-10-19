---
stage: approval
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 9
comments_read: []
handed_over: null
claim: null
journal:
- number: 1
  speaker: factory
  kind: started
  at: '2026-10-19T13:57:40.693817Z'
  stage: acceptance
- number: 2
  speaker: acceptance-reviewer
  kind: result
  at: '2026-10-19T14:01:28.312515Z'
  stage: acceptance
  run: de1ab6c22c654f869404fad1fec153e8
stories: [F0002-S0001, F0002-S0002, F0002-S0003]
outcome: null
---

# Acceptance of Operations

## Recommendation

**accepted.** The three scope items are built, and the feature's goal holds end to end. An operator can tell from outside that the service is up (`/health`), which version runs (`/health` and `python -m app --version`), which storage it uses, and how many todos are open and done (`/stats`). The feature smoke test is green, and so is `make check`. On a copy, the only mutation survivors are equivalent ones. `make mutants` is still red on the merged code, as it was at F0001's acceptance, for the same reason (the `TodoService.list` annotation). F0001-S0005 is the story for that, and it waits in F0001's backlog. I propose one small documentation story.

## 1 Scope

None. Each scope item has its story and its code:
- `GET /health` (status, version, storage kind): S0001, in `src/app/api/health.py`, `HealthRead` and `StorageKind` in `schemas.py`, and `build_app` with `_storage_kind` in `main.py`.
- `python -m app --version`: S0002, in `src/app/__main__.py`.
- `GET /stats` (open, done, total): S0003, in `TodoStats` and `TodoService.stats` in `src/app/service/todo_service.py`, `StatsRead` in `schemas.py`, and `src/app/api/stats.py`.

No story built anything from *Out of scope*: there is no metrics export, no logging configuration, no deployment and no authentication.

The goal is reached, with one nuance that goes under 6. `/health` is a liveness check: it never touches the repository. A SQLite file that cannot be opened at start keeps the server from starting at all, so in that case the monitor sees no answer rather than a 200.

## 2 Feature smoke test

**Green.** As an operator, I walked through the version command, then health and stats over a SQLite file, with creates, a completion, a delete, a reopen and a restart on the same file. Then health in memory, then the module-level `app` that uvicorn serves.

```bash
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
uv run python -m app --version; echo "exit $?"
uv run python -m app --help; echo "exit $?"
TODO_DB="$d/todo.db" uv run python - <<'PY' 2>/dev/null
import os
from fastapi.testclient import TestClient
from app.api.main import build_app
c = TestClient(build_app(os.environ))
print("health", c.get("/health").status_code, c.get("/health").json())
print("stats empty", c.get("/stats").json())
ids = [c.post("/todos", json={"title": t}).json()["id"] for t in ("Buy milk", "Write the docs", "Call mum")]
c.patch(f"/todos/{ids[0]}", json={"done": True})
print("stats", c.get("/stats").json())
c.delete(f"/todos/{ids[1]}")
print("stats after delete", c.get("/stats").json())
c.patch(f"/todos/{ids[0]}", json={"done": False})
print("stats after reopen", c.get("/stats").json())
c2 = TestClient(build_app(os.environ))
print("restart health", c2.get("/health").json())
print("restart stats", c2.get("/stats").json())
print("memory health", TestClient(build_app({})).get("/health").json())
PY
TODO_DB="$d/todo.db" uv run python -c "
from fastapi.testclient import TestClient
from app.api.main import app
print(TestClient(app).get('/stats').json(), TestClient(app).get('/health').json()['storage'])
" 2>/dev/null
```

```
app 0.1.0
exit 0
usage: python -m app --version
exit 2
health 200 {'status': 'ok', 'version': '0.1.0', 'storage': 'sqlite'}
stats empty {'open': 0, 'done': 0, 'total': 0}
stats {'open': 2, 'done': 1, 'total': 3}
stats after delete {'open': 1, 'done': 1, 'total': 2}
stats after reopen {'open': 2, 'done': 0, 'total': 2}
restart health {'status': 'ok', 'version': '0.1.0', 'storage': 'sqlite'}
restart stats {'open': 2, 'done': 0, 'total': 2}
memory health {'status': 'ok', 'version': '0.1.0', 'storage': 'memory'}
{'open': 2, 'done': 0, 'total': 2} sqlite
```

I also checked two claims about the database:
- **Removed after start.** I deleted the database's directory after the app had started. `/health` still answered `200 {'status': 'ok', 'version': '0.1.0', 'storage': 'sqlite'}`.
- **Unreadable at start.** With `TODO_DB=/nonexistent/dir/x.db`, `build_app` raises `sqlalchemy.exc.OperationalError: ... unable to open database file`, so there is no server to answer.

Both match `docs/api.md` *Storage*. *Health* states only the first case on its own (see 5).

`make check` as I found it: `check: green`, 173 passed, total coverage 99.43%. The only line it reports as missed is `src/app/__main__.py:21`.

## 3 Mutation score

**`make mutants FEATURE=F0002` is red on the merged code**, for the same reason as at F0001's acceptance:

```
  File "/work/checkout/mutants/src/app/service/todo_service.py", line 154, in TodoService
    def xǁTodoServiceǁlist__mutmut_orig(self, *, done: bool | None = None) -> list[Todo]:
TypeError: 'function' object is not subscriptable
ERROR tests/api/test_health.py - TypeError: 'function' object is not subscrip...
failed to collect stats. runner returned 1
make: *** [Makefile:109: mutants] Error 1
```

S0003 changed `todo_service.py`, so the module is in this feature's set, and mutmut's rewritten class breaks on `list[Todo]`. The official score is **0/0**. The fix has been proposed already: `F0001-S0005-make-mutants-runs-on-the-service.md` sits unstarted in F0001's backlog. I propose no second story for it. Until that story is merged, every feature that touches the service will be red here.

To still get a score, I ran mutmut 3.8.0 on a throw-away copy of the tracked files in `$TMPDIR`. The one change in that copy was `from __future__ import annotations` in `todo_service.py`. I ran it over the seven modules that the F0002 commits changed: `app.__main__`, `app.api.app`, `app.api.health`, `app.api.main`, `app.api.schemas`, `app.api.stats` and `app.service.todo_service`. **103 killed, 3 survived, of 106 (97.2%).** `health.py` and `stats.py` produced no mutants. The survivors:

| Module | Mutant | Change | Judgement |
| :- | :- | :- | :- |
| `app.__main__` | `main` 16 | `version('app')` → `version('APP')` | Equivalent: distribution names are looked up normalised, so `APP` finds `app`. |
| `app.api.main` | `_storage_kind` 6, 8 | `environ.get("TODO_DB", "")` → default `None` or none | Equivalent: both take the memory branch, the same survivor F0001 recorded for `build_repository`. |

No real survivors, so no missing criteria. I deleted the copy afterwards.

## 4 What the stories noticed

These are collected from the coder, reviewer, documenter and smoke-tester entries of S0001 to S0003:
- **The `StorageKind` alias in place of the spelled-out Literal** (S0001 coder 7, reviewer 9, documenter 11). It means the same thing and keeps the two kinds in one place. No action.
- **`app.state.storage` is untyped** (S0001 reviewer 9). It is assigned to a `StorageKind` variable and validated straight away by `HealthRead`. No action.
- **`sys.exit(main())` in `__main__.py` is reported uncovered** (S0002 coder 9, 17). The child-process test runs it, but coverage does not measure the child. It is the only missed line in the suite, and the gate is 90%. Measuring subprocesses would need `pyproject.toml`, which is the human's file. No story.
- **`StarletteDeprecationWarning`: "install `httpx2` instead"** (S0002 and S0003 coders, S0003 documenter, S0001 and S0003 smoke-testers). It is printed 20 times per `make test`, and on stderr in every smoke test that uses `TestClient`. It is a dependency change, so it is not allowed without asking. F0001's acceptance left it to the human, and so do I.
- **`docs/decisions.md` does not exist** (S0003 documenter 11). Already proposed as F0001-S0008, which is unstarted. No second story.
- **The `belongs_to` and `HTTP_METHODS` helper copies** (S0002 reviewer 11, S0003 tester 5). Both were fixed inside the stories under the standing leave. Nothing is left.
- **A count the database does itself would mean extending the protocol** (S0003 coder 7, written into the project guide). It is a known limit for many todos, with nothing to do now.

## 5 Documentation as a whole

I read `README.md`, `docs/api.md` and `docs/project-guide.md` from the top as a newcomer. The examples I ran match what the documents print: `python -m app --version`, both usage cases, the `/health` and `/stats` bodies, and the empty `/stats`. I found no contradiction between the three documents or with the code. *Storage*, *Health*, the project guide's *Choosing the repository* and the README all describe the `TODO_DB` rule the same way.

Findings, all small:
- **`docs/project-guide.md` line 5, "Built so far"**, names the domain, the repositories, the service and the HTTP API with its storage choice. It leaves out `/health`, `/stats` and the version command, although the guide describes all three further down. Proposed: F0002-S0004.
- **`docs/api.md` *Health*** says that the endpoint "answers 200 also when the database cannot be read". That holds after start. *Storage* says that a file that cannot be opened stops the server at start, but *Health* does not point there, and an operator setting up a monitor reads *Health*. Proposed: F0002-S0004.
- **The README's intro** still says "It is being built story by story". That is already part of F0001-S0008.

## 6 Decisions taken for the human

The nine decisions in `feature.md` (1 to 9) stand as listed there, and I do not repeat them. None of them came from an answer during this feature: no question was asked.

The decisions and defaults taken inside the stories and not written in `feature.md`, to accept or revisit:
1. **One private rule, `_storage_kind(environ)`, serves both `build_repository` and `build_app`**, so the reported storage and the chosen repository cannot drift apart. Rejected: an `isinstance` check on the repository. (S0001 coder 7)
2. **`StorageKind = Literal["memory", "sqlite"]` is a named alias in `schemas.py`**, used by `HealthRead` and `create_app`. (S0001 coder 7)
3. **`/health` is liveness only.** A 200 means the process is up, not that the todos are reachable. If the database cannot be opened at start, there is no server and no answer. A readiness check that touches the repository was not asked for, and it would contradict feature decision 1. (S0001 story text and documenter 11; observed in section 2)
4. **The version command compares the arguments with exactly `["--version"]` and does not use `argparse`.** So `--help` is a usage error with exit 2, not a help text with exit 0. (S0002 coder 9)
5. **`stats()` derives `open` as `len(todos) - done`**, in one pass over one `list_all`. Rejected: a repository count method, and filtering twice. (S0003 coder 7)
6. **The S0003 documenter added the missing `/health` row to `docs/api.md`'s endpoint table**, beyond that story's docs criterion. (S0003 documenter 11)
7. **Feature smoke tests and story smoke tests judge "one line" on stdout.** The Starlette warning on stderr was not counted. (S0001 smoke-tester 13)

Earlier tests changed, with the leave each was changed under (checked against `git log --name-status` of the story commits):
- `tests/api/test_imports.py` and `tests/domain/test_imports.py` (S0002): `_is_repository` and `_is_forbidden` now use the new shared `belongs_to` in `tests/imports.py`. Standing leave to move a shared helper, named by the tester (15) and the reviewer (19).
- `tests/imports.py` (S0002): only adds `belongs_to`. The reviewer (19) named it as needing no leave.
- `tests/api/test_health.py` and `tests/api/test_openapi.py` (S0003): the copied `HTTP_METHODS` moved to `tests/fakes.py`. Standing leave, named by the tester (5) and the reviewer (9).
- `tests/fakes.py` (S0003): gains `HTTP_METHODS`. Standing leave, named by the reviewer (9).

No earlier test was changed without a named leave.

## 7 Slow checks

- **Beyond `make check` and `make mutants`:** nothing. There is no image scan and no SBOM target.
- **Test times**, from `.reports/junit.xml` of my `make check` run: no slow test. The suite took 4.2 s on all cores. The slowest five are SQLite tests, from 0.067 s to 0.096 s. The slowest is `tests/api/test_health.py::test_build_app_hands_the_todo_routes_the_chosen_repository[sqlite]` at 0.096 s, followed by `tests/repository/test_sqlite.py::test_title_with_quotes_and_sql_is_stored_verbatim` at 0.082 s.
- **Disk:** used is unchanged since the previous record, which is F0001's acceptance: `/work` 0.4 GB, `/state` 0.0 GB, `/tmp` 0.0 GB. Free went from 978.7 GB to 978.6 GB on all three mounts alike. That is the shared host volume, not growth in any of them. `.venv` is 482 MB, `mutants/` 784 KB and `.reports/` 104 KB. No unexplained growth.

## 8 Cost

The stories cost **22 runs, 11.0 min, 101 turns, 488,324 tokens in (1,477,371 more from cache), 48,472 out, $3.13**.

| Story | Runs | Minutes | Dollars | Why |
| :- | -: | -: | -: | :- |
| S0001 | 6 | 3.3 | $0.89 | One pass through every stage |
| S0002 | 10 | 4.3 | $1.29 | A crash in the tests stage (journal 5: the run ended without a result and its work was discarded), and one review round. The reviewer found a third copy of the layer check, so the coder handed over to the tester for `belongs_to`, then the coder and the reviewer ran again |
| S0003 | 6 | 3.4 | $0.95 | One pass |

S0002 stands out, although it is the smallest story. It was the only one with a crash and the only one with a rework round, and both its extra runs and its extra dollars come from those. The round itself was cheap: the coder runs cost $0.10 and $0.12.

Human interventions: **0 questions answered, 0.0 h waited.** No story needed the human.

## Proposed stories

- `backlog/F0002-S0004-guides-name-the-operations.md`: a documentation repair. The project guide's "Built so far" line leaves out the three operations, and `docs/api.md` *Health* does not say that a database that cannot be opened at start means no answer at all, not a 200.

I add no story for the red `make mutants`: F0001-S0005 is already in F0001's backlog for it, and I recommend starting it next. All mutation survivors are equivalent.

## Journal

1. factory: started acceptance as opencode-demo.
2. acceptance-reviewer: accepted; 1 stories proposed; make mutants 0/0 (red: mutmut's rewritten service module does not import, as at F0001's acceptance, F0001-S0005 pending); 103/106 on a temporary copy patched only in `todo_service.py`
   1. Scope: none. `/health`, `python -m app --version` and `/stats` each have their story and code. Nothing from Out of scope was built, and the goal is met. `/health` is liveness only.
   2. Feature smoke test: green. I ran the version command (exit 0 and 2), health and stats over a SQLite file through create, complete, delete, reopen and restart, health in memory, and the module-level `app`. `make check` is green: 173 passed, coverage 99.43%.
   3. Mutants: `make mutants FEATURE=F0002` is red with `TypeError: 'function' object is not subscriptable`. The cause is the `TodoService.list` annotation, and F0001-S0005 (unstarted) is the fix. On a temporary copy with `from __future__ import annotations` in `todo_service.py`: 103/106 killed. The 3 survivors are equivalent (`version('APP')`, and the `TODO_DB` default `None`).
   4. Noticed: the uncovered `sys.exit(main())` line (child process), the httpx2 deprecation warning (a dependency change, the human's call), the missing `docs/decisions.md` (already F0001-S0008), and the untyped `app.state.storage` (validated straight away). None needs a new story.
   5. Documentation: no contradiction, and the examples run. The project guide's "Built so far" line leaves out the operations. `docs/api.md` *Health* does not say that a database that cannot be opened at start means no answer at all. Both go to F0002-S0004. The README intro is stale, already in F0001-S0008.
   6. Decisions: the 9 in `feature.md` plus 7 from the stories, listed (`_storage_kind` as one rule, the `StorageKind` alias, health as liveness only, exact `--version` without argparse, open = len − done, the `/health` table row, stdout-only "one line"). The earlier tests changed were `api/test_imports.py`, `domain/test_imports.py`, `imports.py`, `api/test_health.py`, `api/test_openapi.py` and `fakes.py`, each under a named leave. None was changed without one.
   7. Slow checks: none beyond `make check` and `make mutants`. The slowest test takes 0.096 s (`test_build_app_hands_the_todo_routes_the_chosen_repository[sqlite]`). Disk used is unchanged since F0001's acceptance. Free fell by 0.1 GB on all mounts alike (the shared host volume).
   8. Cost: 22 runs, 11.0 min, $3.13. S0002 stands out with 10 runs and $1.29, from one tests-stage crash and one review round about a copied layer check (`belongs_to`). 0 questions answered, 0.0 h waited.
