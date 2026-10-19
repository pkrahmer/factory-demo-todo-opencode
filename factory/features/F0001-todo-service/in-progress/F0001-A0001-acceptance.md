---
stage: approval
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 5
comments_read: []
handed_over: approval
claim: null
journal:
- number: 1
  speaker: factory
  kind: started
  at: '2026-10-19T13:24:06.697745Z'
  stage: acceptance
- number: 2
  speaker: acceptance-reviewer
  kind: result
  at: '2026-10-19T13:28:52.954136Z'
  stage: acceptance
  run: 9b2fbeb24a0241209fac57440abe29f4
stories: [F0001-S0001, F0001-S0002, F0001-S0003, F0001-S0004]
outcome: null
---

# Acceptance of Todo service

## Recommendation

**Accepted with stories.** The four stories together do what `feature.md` promised. Over real uvicorn processes, a todo can be created, listed, filtered by `done`, renamed, completed, reopened and deleted. It survives a restart with `TODO_DB` and is gone without it. `make check` is green, and nothing in the documentation misleads a user.

The proposed stories address four findings:
- `make mutants FEATURE=F0001` cannot run on the code as merged. The method name `TodoService.list` shadows the built-in in mutmut's rewritten class.
- Two mutation gaps: UTC conversion is only tested on a machine whose local zone is UTC, and the naive-time message is untested.
- The PATCH double write, which the documentation itself calls "worth revisiting".
- The decision log that `CLAUDE.md` names but nobody wrote.

## 1 Scope

None. Each scope item of `feature.md` has a story, and the code they name is there:
- **Entity, title rule, timestamps, errors, protocol:** S0001, in `src/app/domain/{model,errors,repository}.py`.
- **In-memory and SQLite repositories, proven equal by one contract suite:** S0001 and S0004, in `src/app/repository/{memory,sqlite}.py`. The suite `tests/repository/test_contract.py` is parametrized over both.
- **Service with create, get, list with done filter, rename, complete, reopen, delete:** S0002, in `src/app/service/todo_service.py`.
- **HTTP API with one error shape and the committed `docs/openapi.json`:** S0003, in `src/app/api/*`. A test keeps `docs/openapi.json` current.
- **Persistence switch through `TODO_DB`:** S0004, `build_repository` in `src/app/api/main.py`.

No story reaches into Out of scope: there is no authentication, front end, search, due date, priority, tag or operations endpoint, and lists are in creation order only. The Goal's "done when" sentence is met; section 2 shows it end to end.

## 2 Feature smoke test

A user's walk-through against the real entry point: `uvicorn app.api.main:app` on a `TODO_DB` file, restarted, then once more without `TODO_DB` in an empty directory. The script lived in `$TMPDIR/feature_smoke.sh`: it started uvicorn on port 8766 in a `mktemp -d` directory with a trap that stopped it, and drove it with `curl`. Command: `bash "$TMPDIR/feature_smoke.sh"`. Its steps:

1. Create three todos (the first with a padded title).
2. List all of them.
3. Rename B with a padded title.
4. Complete A and C, then reopen C.
5. Filter by `done=true` and by `done=false`.
6. Delete C, then GET it.
7. Send three refused requests: a blank title, a 201-character title, an empty PATCH.
8. Restart on the same `TODO_DB`, then list and GET A.
9. Start an in-memory server in an empty directory, create a todo, restart, list, and count the files in the directory.

Output:

```
# list all
[{"id":"b4e546b6-6ed5-4528-9954-21690e69a500","title":"Buy milk","done":false,"created_at":"2026-10-19T13:24:48.648400Z"},{"id":"7e7a4ef3-56f8-4d50-aa8a-ca1590b10844","title":"Write the report","done":false,"created_at":"2026-10-19T13:24:48.674665Z"},{"id":"80094489-36bf-4e70-8f42-55867c5fe28b","title":"Call mum","done":false,"created_at":"2026-10-19T13:24:48.700906Z"}]
# rename B
{"id":"7e7a4ef3-56f8-4d50-aa8a-ca1590b10844","title":"Write the acceptance report","done":false,"created_at":"2026-10-19T13:24:48.674665Z"}
# complete A and C
{"id":"b4e546b6-6ed5-4528-9954-21690e69a500","title":"Buy milk","done":true,"created_at":"2026-10-19T13:24:48.648400Z"}
{"id":"80094489-36bf-4e70-8f42-55867c5fe28b","title":"Call mum","done":true,"created_at":"2026-10-19T13:24:48.700906Z"}
# reopen C
{"id":"80094489-36bf-4e70-8f42-55867c5fe28b","title":"Call mum","done":false,"created_at":"2026-10-19T13:24:48.700906Z"}
# filter done=true
[{"id":"b4e546b6-6ed5-4528-9954-21690e69a500","title":"Buy milk","done":true,"created_at":"2026-10-19T13:24:48.648400Z"}]
# filter done=false
[{"id":"7e7a4ef3-56f8-4d50-aa8a-ca1590b10844","title":"Write the acceptance report","done":false,"created_at":"2026-10-19T13:24:48.674665Z"},{"id":"80094489-36bf-4e70-8f42-55867c5fe28b","title":"Call mum","done":false,"created_at":"2026-10-19T13:24:48.700906Z"}]
# delete C
204
# get C
{"detail":"todo 80094489-36bf-4e70-8f42-55867c5fe28b not found"}
# blank title, 201 chars, empty patch
{"detail":"title must not be blank"}
{"detail":"title must be at most 200 characters"}
{"detail":"body: Value error, set title or done"}
# restart
# list after restart
[{"id":"b4e546b6-6ed5-4528-9954-21690e69a500","title":"Buy milk","done":true,"created_at":"2026-10-19T13:24:48.648400Z"},{"id":"7e7a4ef3-56f8-4d50-aa8a-ca1590b10844","title":"Write the acceptance report","done":false,"created_at":"2026-10-19T13:24:48.674665Z"}]
# get A after restart
{"id":"b4e546b6-6ed5-4528-9954-21690e69a500","title":"Buy milk","done":true,"created_at":"2026-10-19T13:24:48.648400Z"}
# in memory: no TODO_DB, restart loses todos
[{"id":"812a1a22-a36e-44ce-b22e-fdf95543
[]
0
```

**Green.** Every step behaves as the feature promises:
- Titles are stripped.
- Lists are in creation order.
- The filter works on both sides, and the reopen shows in the `done=false` list.
- Errors come back as one `{"detail": ...}` sentence.
- After the restart, A is still done, B keeps its new title and C is still deleted.
- The in-memory server writes no file (`0`), and its todos are gone after its restart (`[]`).

I also checked the error examples in `docs/api.md` through `TestClient(app.api.main.app)`: `path.todo_id: Input should be a valid UUID, invalid character: found `x` at 0` and `query.done: Input should be a valid boolean, unable to interpret input` match word for word.

`make check`, run first and as I found it: `check: green`, with 146 passed and 100 % coverage.

## 3 Mutation score

**`make mutants FEATURE=F0001` is red on the merged code.** pytest cannot import mutmut's rewritten service module:

```
  File "/work/checkout/mutants/src/app/service/todo_service.py", line 139, in TodoService
    def xǁTodoServiceǁlist__mutmut_orig(self, *, done: bool | None = None) -> list[Todo]:
TypeError: 'function' object is not subscriptable
ERROR tests/api/test_main.py - TypeError: 'function' object is not subscriptable
failed to collect stats. runner returned 1
make: *** [Makefile:109: mutants] Error 1
```

mutmut puts its copies of `list` after the method `list` in the class body. There, `list[Todo]` names the method, not the built-in. S0002's coder named exactly this risk in journal 7, and the reviewer and documenter repeated it. The official score is therefore **0/0**.

To have a score at all, I ran mutmut 3.8.0 (`mutmut run 'app.*'`) on a throw-away copy of the tracked files in `$TMPDIR`. The only change in that copy was `from __future__ import annotations` in `todo_service.py`. The repository was not changed. **226 killed, 8 survived of 234 (96.6 %).** The survivors, read with `mutmut show`:

| Module | Mutant | Change | Judgement |
| :- | :- | :- | :- |
| `app.domain.model` | `_in_utc` 5 | `astimezone(UTC)` → `astimezone(None)` | Real gap: converts to the machine's local zone. It is only invisible because the test machine's local zone is UTC. |
| `app.repository.sqlite` | `_stored_created_at` 2 | `astimezone(UTC)` → `astimezone(None)` | Same gap: local times would be stored with a `+00:00` label. |
| `app.domain.model` | `_in_utc` 2, 3, 4 | `ValueError` message `None`, `XX…XX`, upper case | Real but small: no criterion fixes the naive-time message. |
| `app.repository.sqlite` | `__init__` 5 | `create_all(engine, checkfirst=True)` → `create_all(engine)` | Equivalent: `checkfirst` defaults to `True`. |
| `app.api.main` | `build_repository` 3, 5 | `environ.get("TODO_DB", "")` → default `None` or none | Equivalent: `not None` takes the memory branch too. |

The real survivors group into two missing criteria: UTC conversion independent of the machine's zone (domain and SQLite), and the naive-time message. Both go into F0001-S0006. The red run itself goes into F0001-S0005.

## 4 What the stories noticed

Collected from the coder, reviewer and documenter entries of S0001–S0004, with what becomes of each:
- **`TodoService.list` shadows the built-in** (S0002 coder 7, reviewer 9, documenter 11). It is no longer harmless: it is what breaks `make mutants` (section 3). Proposed: S0005.
- **`PATCH` with both fields makes two repository writes** (S0003 coder 10). S0004's documenter wrote into `docs/api.md` that with SQLite a failure between them leaves the rename without the `done` change, "worth revisiting". Proposed: S0007.
- **`docs/decisions.md` does not exist although `CLAUDE.md` names it** (S0001 documenter 11, S0002 documenter 11, S0003 documenter 14). S0003's documenter also noted that the typed-handler decision lives only in the journal. Proposed: S0008.
- **`StarletteDeprecationWarning`: "install `httpx2` instead"** (S0003 coder 10, S0004 coder 7). It is printed 20 times per `make test`. Moving to `httpx2` is a dependency change and "not without asking", so I propose no story; it is the human's call.
- **`DuplicateTodo` has no status mapping** (S0003 coder 10). No request can cause it, because ids are generated server-side, and `docs/project-guide.md` records this. No action.
- **Each `from_path` creates an engine and never disposes it** (S0004 coder 7). This is documented in the project guide and harmless for a server process. No action.
- **`_todo_from_row`'s typed `Row[str, str, bool, str]` is not proven by mypy, since `select(_todos)` is untyped** (S0004 coder 11). Only the tests hold the column types. The contract suite and criterion 11 of S0004 cover it. No action.
- **`T0` is still a copy in `tests/domain/test_model.py`** (S0004 tester 5, which rejected moving it). It is a candidate for the standing helper-move leave the next time a story touches the domain tests. No story.
- **The README intro said "kept in memory or in a SQLite file" before SQLite existed** (S0003 documenter 14). It is true now. The sentence beside it, "It is being built story by story; this README grows with it", is stale once the feature is complete; it is folded into S0008.
- **Pydantic's wording after the location prefix may change with its version** (S0003 documenter 14). `docs/api.md` already says only the prefix is stable. No action.

## 5 Documentation as a whole

I read `README.md`, `docs/api.md` and `docs/project-guide.md` top to bottom as a newcomer. I found no contradiction between them and no contradiction with the code:
- Title rules, error shape, `PATCH` rules, storage formats and the `TODO_DB` rules agree across the three files and with `src/app`.
- The examples I ran (both *Try it* blocks of the guide, the README's server starts and curls inside the feature smoke test, and the validation-error examples of `docs/api.md`) print what the documents say.

The overlap is deliberate and consistent. `docs/api.md` (*Storage*) and `docs/project-guide.md` (*SQLite repository*) both describe the stored format; the guide points to `api.md` for the operator's view.

Gaps:
- `docs/decisions.md`, which `CLAUDE.md` and the rules (R4) rely on, was never written (S0008).
- The README intro still speaks of a service being built.
- `docs/api.md` ends its *PATCH rules* with an open design question ("It is worth revisiting"). That is honest, but it is a to-do in a reference document (S0007).

## 6 Decisions taken for the human

The 18 decisions in `feature.md` (*Decisions taken for the human*, 1–18) stand as listed there. I do not repeat them. Two of them came from answers:
- **Decision 18:** the human's answer (c) on S0003's intake question.
- **Decision 12:** the shakedown's intake question.

Decisions and defaults taken inside the stories and not in `feature.md`, for the human to accept or revisit:
1. **All title and time rules sit in `Todo.__post_init__`.** `new`, `with_title` and `with_done` go through the constructor. Rejected: a validating factory beside a plain constructor. (S0001 coder, journal 7)
2. **The done filter runs in the service over `list_all()`.** The protocol has no filtered list. Rejected: a filtered list method on the protocol. Consequence: SQLite reads every row for a filtered list. (S0002 coder, journal 7)
3. **Domain error handlers are typed functions registered with `app.exception_handler(type)`.** Rejected: `add_exception_handler` with `Exception`-typed handlers. (S0003 coder, journal 10)
4. **`DuplicateTodo` has no HTTP mapping**, because the Interface's table leaves it out. If it were ever raised, it would surface as a 500. (S0003 coder, journal 10; recorded in the project guide)
5. **`PATCH` with both fields is two writes, not one transaction.** This is a default by omission. (S0003 coder, journal 10; proposed to revisit in S0007)
6. **`created_at` is stored as fixed-width text, `%Y-%m-%dT%H:%M:%S.%f+00:00`, and the database sorts (`ORDER BY created_at, id`).** Rejected: `isoformat()` plus sorting in Python. (S0004 coder, journal 7)
7. **The row type is spelled `Row[str, str, bool, str]`** (SQLAlchemy 2.1), not the reviewer's `Row[tuple[...]]`. (S0004 coder, journal 11)
8. **A relative `TODO_DB` is relative to the server's working directory, and a missing parent directory makes the server fail to start.** This was observed and documented, not chosen. (S0004 documenter, journal 15)
9. **Criterion 5 of S0002 was left ambiguous** about which todos are completed, without asking. (S0002 intake, journal 3)
10. **`make mutants` cannot run while `TodoService.list` is annotated `list[...]`.** Keeping the method name and spelling the type `builtins.list` (S0005 as proposed), against renaming the method, is the human's choice.

Earlier tests changed, with their leave:
- **`tests/service/test_todo_service.py`** (S0003): `T0` and `TickingClock` moved to `tests/fakes.py`. Standing leave to move a shared helper, named by the tester (8) and the reviewer (12).
- **`tests/domain/test_imports.py`** (S0003): `_imported_modules` moved to `tests/imports.py` as `imported_modules`. Standing leave, named by the tester (8) and the reviewer (12).
- **`tests/repository/test_contract.py`** (S0004): the `_sqlite` factory and the `SqliteTodoRepository` class row were added under the human's leave in S0004's Interface. `make_todo` and its `T0` copy moved to `tests/fakes.py` under the standing leave. Named by the tester (5) and the reviewer (9, 13).
- **`tests/fakes.py`** (S0004): gained `make_todo` under the standing leave. Named by the reviewer (9, 13).

`git log --name-status` of the story commits shows no other modified test (`M`). No earlier test was changed without a named leave.

## 7 Slow checks

- **Checks beyond `make check` and `make mutants`:** none. There is no image scan and no SBOM target.
- **`make duplicates`:** last reported by S0004's coder as `0 similar code, 6 dead code`.
- **Test times:** the JUnit report `.reports/junit.xml` of my `make check` run shows no slow test. The slowest five are all SQLite tests, from 0.063 s to 0.088 s; the slowest is `tests/api/test_main.py::test_todos_persist_across_apps_on_the_same_file`. The whole suite took 3.8 s on all cores.
- **Disk:** `/work` went from 0.0 GB used at the start record to 0.4 GB now, with 1.0 GB less free. That is explained by the project environment: `.venv` is 482 MB, from `uv sync` of the pinned dependencies, and `mutants/` (712 KB) and `.reports/` (100 KB) are mine. `/state` and `/tmp` are unchanged at 0.0 GB used. No unexplained growth.

## 8 Cost

The stories cost **27 runs, 20.2 min, 139 turns, 733,026 tokens in (2,545,470 more from cache), 107,453 out, $5.35**.

| Story | Runs | Minutes | Dollars | Why |
| :- | -: | -: | -: | :- |
| S0001 | 6 | 4.3 | $1.13 | One pass through every stage |
| S0002 | 6 | 3.1 | $0.92 | One pass |
| S0003 | 7 | 6.3 | $1.65 | One extra intake run for the question. It is the largest story: six modules, 24 criteria and the OpenAPI file |
| S0004 | 8 | 6.5 | $1.65 | One review round: the `Row[Any]` finding against the `Any` rule, fixed in round 1 |

No story stands out beyond what its size and that one round explain.

Human interventions: **1 question answered (cause: question), 0.0 h waited.** The story that needed the human was S0003. Its intake asked whether `POST /todos` needed a criterion for the stripped, padded title, because a schema-side `max_length` would have passed every criterion. The human chose (c), both: criterion 24 and a padded row in criterion 3, now feature decision 18.

## Proposed stories

- `backlog/F0001-S0005-make-mutants-runs-on-the-service.md`: `make mutants` is red because `TodoService.list` shadows the built-in in mutmut's rewritten class. This story spells the type `builtins.list` and keeps the method name.
- `backlog/F0001-S0006-utc-holds-on-a-machine-outside-utc.md`: the five real mutation survivors. UTC conversion in the domain and the SQLite repository is only tested where the local zone is UTC, and the naive-time message is untested.
- `backlog/F0001-S0007-patch-in-one-write.md`: `PATCH` with title and done is two writes, which `docs/api.md` itself flags. A `TodoService.change` would make it one.
- `backlog/F0001-S0008-decision-log.md`: `docs/decisions.md` is named by `CLAUDE.md` but was never written, and the README intro is stale. This story adds a test that every named `docs/*.md` exists.

## Journal

1. factory: started acceptance as opencode-demo.
2. acceptance-reviewer: accepted with stories; 4 stories proposed; make mutants 0/0 (red: mutmut's rewritten service module does not import); 226/234 on a temporary copy patched only in `todo_service.py`
   1. Scope: none. Every scope item has a story and code; nothing from Out of scope was built; the Goal is met.
   2. Feature smoke test: green. Over two real uvicorn runs on one `TODO_DB` file, todos were created, listed, filtered both ways, renamed, completed, reopened and deleted, with errors refused, and they survived the restart. In memory: no file written and the todos were gone after a restart. `make check` is green.
   3. Mutants: `make mutants FEATURE=F0001` fails with `TypeError: 'function' object is not subscriptable`. Inside the class, `TodoService.list` hides the built-in, so mutmut's copies of the method annotated `list[Todo]` break the import. On a temporary copy patched only with `from __future__ import annotations`: 226/234 killed. Survivors: 3 equivalent; UTC conversion only tested where local time is UTC (domain and SQLite, 2 mutants); naive-time message untested (3). Stories S0005 and S0006.
   4. Noticed: the `list` shadowing (now a breakage) goes to S0005; PATCH's two writes to S0007; the missing `docs/decisions.md` to S0008. Left with no story: the httpx2 deprecation warning (a dependency change, the human's call), the unmapped `DuplicateTodo`, the engines that are never disposed, the untyped `select` row and the `T0` copy in the domain tests.
   5. Documentation: no contradiction and every example I ran works. Missing: `docs/decisions.md`. Stale: the README intro ("being built story by story"). `docs/api.md` ends PATCH with an open question.
   6. Decisions: the 18 in `feature.md` plus 10 from the stories' journals, listed. Earlier tests changed: `test_todo_service.py`, `domain/test_imports.py`, `test_contract.py` and `fakes.py`, each with a named leave. None changed without one.
   7. Slow checks: none beyond `make check` and `make mutants`. The slowest test is 0.088 s. `/work` grew by 0.4 GB, explained by `.venv` (482 MB) plus `mutants/` and `.reports/`.
   8. Cost: 27 runs, 20.2 min, $5.35. S0003 and S0004 cost $1.65 each: S0003 is the largest story and had one intake question; S0004 had one review round over `Row[Any]`. One question was answered by the human (S0003's padded-title criterion), with 0.0 h waited.
