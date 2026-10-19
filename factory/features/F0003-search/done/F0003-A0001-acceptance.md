---
stage: done
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 11
comments_read: []
handed_over: approval
claim: null
journal:
- number: 1
  speaker: factory
  kind: started
  at: '2026-10-19T14:17:37.217601Z'
  stage: acceptance
- number: 2
  speaker: acceptance-reviewer
  kind: result
  at: '2026-10-19T14:21:22.406908Z'
  stage: acceptance
  run: ae2ea068082a4717bf97753bdb72e0e2
- number: 3
  speaker: factory
  kind: done
  at: '2026-10-19T14:22:41.204807Z'
  stage: done
stories: [F0003-S0001]
outcome: accepted
---

# Acceptance of Search

## Recommendation

**accepted.** The feature meets its Goal: `GET /todos?search=<text>` returns the todos whose title contains the text, ignoring case (with Unicode case folding), and combines with `done`. My end-to-end walk-through gave the same results on both storages, `make check` is green, and the docs agree with the behaviour. The one red check is `make mutants`. That breakage is older than this feature: F0001's acceptance found it and proposed `F0001-S0005-make-mutants-runs-on-the-service.md`, which is still waiting in F0001's backlog. On a throw-away copy with that one-line fix, all 41 mutants of the changed service module are killed. I propose no stories, because the only finding of weight already has one.

## 1 Scope

None. Each part of `feature.md` is covered:
- **Scope item.** The one scope item ("Title search in the service and as a query parameter of `GET /todos`") is S0001. It is built in `src/app/service/todo_service.py`, as `TodoService.list(*, done=None, search=None)`, and in `src/app/api/routes.py`, as `list_todos` with `search: Annotated[str | None, Query(max_length=MAX_TITLE_LENGTH)]`.
- **Out of scope.** Nothing from it was built. There is no index, no ranking and no fuzzy matching, and the repository and domain are unchanged: the service filters `list_all()`.
- **Goal.** It is met, as section 2 shows.

## 2 Feature smoke test

**Green.** As a user would, I create todos, mark one done, then search: by a word, padded and in mixed case, with case folding, combined with both `done` values, blank, with no match, and at both sides of the length limit. I ran it once with in-memory storage and once with SQLite (`TODO_DB`), through `build_app` and `TestClient`.

Command (a script in a `mktemp -d` folder, removed afterwards; the arguments of `build_app` are `{}` and `{"TODO_DB": "<tmp>/todos.db"}`):

```bash
uv run python "$d/smoke.py" "$d" 2>&1 | grep -v Deprecat | grep -v "from starlette"
```

The script creates `Buy Milk`, `MILK run`, `Call mum` and `Straße fegen`, completes `Buy Milk`, then calls `GET /todos` with the parameters on each line. Output:

```
memory search=milk         ['Buy Milk', 'MILK run']
memory search=' mIlK '     ['Buy Milk', 'MILK run']
memory search=STRASSE      ['Straße fegen']
memory done=true milk      ['Buy Milk']
memory done=false milk     ['MILK run']
memory search=''           ['Buy Milk', 'MILK run', 'Call mum', 'Straße fegen']
memory search='   '        ['Buy Milk', 'MILK run', 'Call mum', 'Straße fegen']
memory search=xyz          []
memory 200 chars           200
memory 201 chars           422 {'detail': 'query.search: String should have at most 200 characters'}
memory padded 201          422 ['detail']
sqlite search=milk         ['Buy Milk', 'MILK run']
sqlite search=' mIlK '     ['Buy Milk', 'MILK run']
sqlite search=STRASSE      ['Straße fegen']
sqlite done=true milk      ['Buy Milk']
sqlite done=false milk     ['MILK run']
sqlite search=''           ['Buy Milk', 'MILK run', 'Call mum', 'Straße fegen']
sqlite search='   '        ['Buy Milk', 'MILK run', 'Call mum', 'Straße fegen']
sqlite search=xyz          []
sqlite 200 chars           200
sqlite 201 chars           422 {'detail': 'query.search: String should have at most 200 characters'}
sqlite padded 201          422 ['detail']
```

Every line matches `feature.md`, its four decisions and `docs/api.md`. The lines I filtered out are the known `StarletteDeprecationWarning` on stderr (see section 4).

`make check` on the branch as I found it: `187 passed`, total coverage 99.44 %, `check: green`.

## 3 Mutation score

**`make mutants` (FEATURE=F0003 from the branch) is red, so the official score is 0/0.** It selects `src/app/service/todo_service.py` and `src/app/api/routes.py`. mutmut's stats run aborts with `BadTestExecutionCommandsException` and does not print pytest's error. I loaded mutmut's config with `debug=True` in-process, which changes nothing in the repository, and that shows the cause:

```
ImportError while loading conftest '/work/checkout/mutants/tests/conftest.py'.
src/app/service/todo_service.py:161: in TodoService
    def xǁTodoServiceǁlist__mutmut_orig(self, *, done: bool | None = None, search: str | None = None) -> list[Todo]:
E   TypeError: 'function' object is not subscriptable
```

This is the breakage F0001's acceptance reported. In mutmut's rewritten class, the method `list` comes before mutmut's copies of it, so their annotation `list[Todo]` names the method, not the built-in. F0003 did not cause it, but it did touch `list` again, so the feature's main function still cannot be measured by the official target. The fix is `F0001-S0005-make-mutants-runs-on-the-service.md`, proposed by F0001's acceptance and still unstarted in `factory/features/F0001-todo-service/backlog/`. I propose no second story for it.

To get a score anyway, I copied the tracked files to `$TMPDIR` and changed only one thing in the copy: `from __future__ import annotations` in `todo_service.py`. Then I ran `mutmut run 'app.service.todo_service.*' 'app.api.routes.*'` (mutmut 3.8.0). The copy was removed afterwards and the repository is unchanged. Results:
- **41 killed of 41, no survivors.** Nine of the mutants are in `TodoService.list`, among them `needle = None`, the casefold and strip removed, and `is` turned into `is not`. All nine are killed.
- **`routes.py` yields no mutants.** mutmut 3 leaves decorated functions alone, so the `Query(max_length=MAX_TITLE_LENGTH)` limit is not mutated. Criterion 8's parametrized test covers it on both sides, including the padded case.

There are no survivor groups and no missing criteria.

## 4 What the stories noticed

The stories noticed three things. None of them needs a new story:
- **`StarletteDeprecationWarning`** ("install `httpx2` instead") from `fastapi.testclient`. Coder entries 7, 11 and 15 and the smoke tester note it. Fixing it means a dependency change, which needs the human under "Not without asking". F0001's acceptance already left it with the human. I leave it there too and propose no story.
- **`src/app/__main__.py` line 21 is not covered** (coder entry 15). The line is older than this feature, and coverage stays 99.44 %, above the 90 % floor. It is too small for a story; I record it here.
- **Reviewer, round 0: three copied fixtures.** They were findings, not remarks, and the tester closed them under the standing leave (entry 13).

The documenter found nothing stale. `make duplicates` reports 0 similar code. It reports 8 dead-code items, all FastAPI route handlers and a Pydantic validator that vulture cannot see being used. They are false positives, and they include `list_todos` only because it is a route.

## 5 Documentation as a whole

No contradictions:
- **The rules agree everywhere.** `README.md`, `docs/api.md` (endpoint table, *List filters*, error table and examples) and `docs/project-guide.md` (service table, *The filters*, `routes` row) state the same search rules. Section 2 shows they match the behaviour, including the `query.search: String should have at most 200 characters` message that `docs/api.md` quotes.
- **The examples work.** I ran the README's `?search=milk` example and the `?search=milk&done=false` example of `docs/api.md` as their `TestClient` equivalents (section 2). I did not run the `curl` forms against a live server.

Two older gaps remain, and F0001's acceptance already proposed both in `F0001-S0008-decision-log.md`:
- `docs/decisions.md`, which `CLAUDE.md` names twice, still does not exist.
- The README intro still says "It is being built story by story; this README grows with it."

This feature made no new section necessary.

## 6 Decisions taken for the human

From `feature.md`, all taken in S0001's story text and all built as written (section 2):
1. **Matching rule.** Search is a case-insensitive substring match on the title with Unicode case folding (`STRASSE` finds `Straße`). The text is stripped first, and an empty text means no filter.
2. **Long searches.** A search longer than 200 characters is a 422, not a silent empty result.
3. **Counting the limit.** The 200 characters are counted on the text as sent, before stripping, so a padded search over 200 characters is a 422. `feature.md` cites "F0003's acceptance at the shakedown, 2026-10-18" for this. There is no such report in git (this report is `F0003-A0001`), so that source cannot be checked from the repository. The decision itself is in S0001's text and criterion 8.
4. **`search=None`.** It means no title filter, like an empty or blank text.

Defaults the stories took without a question:
5. **Fixture name.** The shared service fixture is called `ticking_service`, not `service`, so that `tests/service/test_todo_service.py` keeps its fixed-clock `service` (tester entry 13). This is a test-structure choice, not a product one.
6. **Filtering style.** The service filters in two steps, `done` then `search`, rather than in one comprehension (coder entry 7).
7. **Where the limit lives.** Only the API applies the length limit. `TodoService.list` takes a search text of any length. This follows from the Interface, but it is worth knowing if another caller ever uses the service directly.

Earlier tests changed, each under the standing leave in `CLAUDE.md` (*Tests*) to move a shared helper. The tester named each one (entries 5 and 13) and the reviewer confirmed each (entry 17):
- `tests/api/test_todos.py`: `_assert_only_detail` moved to `tests/responses.py`; the `service` and `client` copies were replaced by the shared fixtures.
- `tests/api/test_stats.py`: the `service` copy was replaced by `ticking_service`.
- `tests/service/test_todo_service.py`: the `ticking_service` copy was removed.
- `tests/conftest.py`: fixtures were only added.

No earlier test was changed without a named leave.

## 7 Slow checks

Nothing to report:
- **Other slow checks.** The project offers none beyond `make check` and `make mutants`: no image scan and no SBOM.
- **Test times.** From `.reports/junit.xml`, the 187 tests take 2.84 s together. The slowest is `tests/api/test_health.py::test_build_app_hands_the_todo_routes_the_chosen_repository[sqlite]` at 0.102 s, then two SQLite repository tests at 0.077 s. The 14 search tests take 0.112 s together.
- **Disk.** The Disk now line equals the previous record line, both "disk acceptance": `/work` 978.6 GB free and 0.4 GB used, `/state` and `/tmp` 0.0 GB used. There is no growth to explain.

## 8 Cost

S0001, the only story, cost 10 runs, 6.6 min, 54 turns, 264,860 tokens in (1,003,600 more from cache) and 28,676 out: **$1.87**.
- **Most expensive runs.** The two tester runs were the largest, $0.34 and $0.41. The second ($0.41, 14 turns, 97 s) was the round-1 fixture move across five test files.
- **The rework round.** Round 0's review found three copied fixtures. Because the coder may not touch tests, the fix went doing → tests → doing → review. That accounts for 4 of the 10 runs, about $0.83.
- **Human interventions.** 0 questions answered, 0.0 h waited. The story never needed the human.

## Proposed stories

None. The one finding of weight, `make mutants` being red on `TodoService.list`, is already proposed as `F0001-S0005-make-mutants-runs-on-the-service.md` in F0001's backlog. Starting that story is the human's call, and it would also make this feature measurable by `make mutants`. The other observations (the dependency warning, one uncovered line in `__main__`, the missing decision log) are either the human's to decide or already proposed in F0001's backlog.

## Journal

1. factory: started acceptance as opencode-demo.
2. acceptance-reviewer: accepted; 0 stories proposed; make mutants 0/0 (red: mutmut's rewritten copy of `todo_service.py` does not import, the `list` shadowing already proposed as F0001-S0005); 41/41 on a temporary copy patched only with `from __future__ import annotations`
   1. Scope: none. The one scope item is built in `todo_service.py` and `routes.py`. Nothing from Out of scope was built. The Goal is met.
   2. Feature smoke test: green on both storages, in memory and SQLite, through `build_app` and `TestClient`. Checked: matching, strip, casefold, both `done` values, blank text, no match, 200 → 200, 201 and padded 201 → 422 with `query.search: `. `make check` is green with 187 tests passed.
   3. Mutants: `make mutants` fails with `TypeError: 'function' object is not subscriptable` because `TodoService.list` shadows the built-in. This is older than F0003, and its fix F0001-S0005 is unstarted. On the patched copy, 41/41 were killed with no survivors. `routes.py` gives no mutants because mutmut skips decorated functions.
   4. Noticed: the httpx/Starlette deprecation warning (a dependency change, the human's call) and `__main__.py` line 21 uncovered (older than F0003). Neither gets a story. The round-0 fixture copies were closed under the standing leave.
   5. Documentation: README, `docs/api.md` and `docs/project-guide.md` agree with each other and with the behaviour. The missing `docs/decisions.md` and the stale README intro are already in F0001-S0008.
   6. Decisions: the 4 in `feature.md` plus 3 defaults from the journals, listed. The shakedown acceptance that decision 3 cites is not in git. Earlier tests `test_todos.py`, `test_stats.py` and `test_todo_service.py` were changed under the standing leave and named. None was changed without a leave.
   7. Slow checks: none beyond `make check` and `make mutants`. The slowest test is 0.102 s and all 187 take 2.84 s. Disk is unchanged against the previous record.
   8. Cost: 1 story, 10 runs, 6.6 min, $1.87. The fixture rework round took 4 runs (about $0.83). 0 questions, 0.0 h waited.
3. factory: done (pull request merged); cost: 1 runs, 3.7 min, 30 turns, 65724 tokens in (1281004 more from cache), 15245 out, $0.89
