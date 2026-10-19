---
stage: tests
blocked: null
round: 1
attempts: 0
crashes: 0
pull_request: 10
comments_read: []
handed_over: null
claim: null
journal:
- number: 1
  speaker: human
  kind: created
  at: '2026-10-19T14:03:37.353581Z'
  stage: intake
- number: 2
  speaker: factory
  kind: started
  at: '2026-10-19T14:03:37.359907Z'
  stage: intake
- number: 3
  speaker: intake
  kind: result
  at: '2026-10-19T14:04:07.925247Z'
  stage: intake
  run: 1505e4f93cd746f4b3858b17035e3923
- number: 4
  speaker: factory
  kind: started
  at: '2026-10-19T14:04:28.569051Z'
  stage: tests
- number: 5
  speaker: tester
  kind: result
  at: '2026-10-19T14:05:44.213277Z'
  stage: tests
  run: 51fb2689995b43038cbd120295dd9b02
- number: 6
  speaker: factory
  kind: started
  at: '2026-10-19T14:06:05.480257Z'
  stage: doing
- number: 7
  speaker: coder
  kind: result
  at: '2026-10-19T14:07:09.411828Z'
  stage: doing
  run: d1f4508ce98e4471a9971e1d03d539fe
- number: 8
  speaker: factory
  kind: started
  at: '2026-10-19T14:07:30.096430Z'
  stage: review
- number: 9
  speaker: reviewer
  kind: result
  at: '2026-10-19T14:07:58.564636Z'
  stage: review
  run: 7a8c8dc080df427181380303a7693a1d
- number: 10
  speaker: factory
  kind: started
  at: '2026-10-19T14:08:19.261669Z'
  stage: doing
- number: 11
  speaker: coder
  kind: result
  at: '2026-10-19T14:08:38.516623Z'
  stage: doing
  run: d7d61a9b134b4e499d9997dfe4d9152f
---

# Title search

## Description

Find todos by a piece of their title: `GET /todos?search=milk` returns the todos whose title contains the text, ignoring case, in creation order, and combines with the existing `done` filter. The service filters what the repository lists, as it does for `done`; no repository change, no domain change.

## Interface

`src/app/service/todo_service.py`

```python
class TodoService:
    def list(self, *, done: bool | None = None, search: str | None = None) -> list[Todo]: ...
```

- `search` is stripped, then matched as a substring of the title after Unicode case folding (`str.casefold`) of both.
- `None`, or a text that is empty after stripping, means no title filter.
- `done` and `search` combine: a todo must satisfy both. The order stays the repository's (creation order).

`src/app/api/routes.py`

```python
@router.get("")   # with the decorator arguments it has today
def list_todos(
    service: Service,
    done: bool | None = None,
    search: Annotated[str | None, Query(max_length=MAX_TITLE_LENGTH)] = None,
) -> list[TodoRead]: ...
```

- A `search` longer than `MAX_TITLE_LENGTH` (200) characters is rejected by the schema with 422, in the API's error shape; one of exactly 200 characters is accepted.

Tests: `tests/service/test_search.py` and `tests/api/test_search.py`.

## Acceptance criteria

1. With todos titled `Buy Milk`, `MILK run` and `Call mum`, `list(search="milk")` returns the first two, in creation order.
2. `list(search="  milk ")` returns the same todos as `list(search="milk")`.
3. `list(search=None)`, `list(search="")` and `list(search="   ")` return the same todos as `list()`: three rows of one parametrized test.
4. Case folding, not just lower case: with a todo titled `Straße`, `list(search="STRASSE")` returns it.
5. With `Buy Milk` done and `MILK run` open, `list(done=False, search="milk")` returns only `MILK run`, and `list(done=True, search="milk")` only `Buy Milk`: two rows of one parametrized test.
6. `GET /todos?search=milk` on the data of criterion 1 returns 200 and the two matching todos, in creation order.
7. `GET /todos?done=true&search=milk` on the data of criterion 5 returns 200 and only `Buy Milk`.
8. The length limit on both sides, counted on the text as sent, as rows of one parametrized test: `GET /todos?search=<200 characters>` returns 200 and `[]` on the data of criterion 1; `GET /todos?search=<201 characters>` returns 422 and a body whose only key is `detail`, a string starting with `query.search: `; and `GET /todos?search=<197 spaces>milk` (201 characters as sent, 4 after stripping) also returns 422 with such a body.
9. `GET /todos` without parameters still returns every todo.
10. `docs/openapi.json` still equals `app.openapi()` of `app.api.main.app` (the existing test of F0001-S0003; the coder runs `make openapi`).
11. `make check` stays green.
12. docs: `docs/api.md` names the `search` parameter in the endpoint table and states its rules in a sentence (stripped, case-insensitive substring, combines with `done`, empty means no filter, at most 200 characters); the README's example shows one `search` call.

## Smoke test

```bash
uv run python -c "
from fastapi.testclient import TestClient
from app.api.main import build_app
c = TestClient(build_app({}))
for t in ('Buy Milk', 'MILK run', 'Call mum'):
    c.post('/todos', json={'title': t})
print([t['title'] for t in c.get('/todos', params={'search': ' milk '}).json()])
r = c.get('/todos', params={'search': 'x' * 201})
print(r.status_code, list(r.json()))
"
```

Expect: two lines, `['Buy Milk', 'MILK run']`, then `422 ['detail']`.

## Journal

1. 2026-10-19 human: created.
2. factory: started intake as opencode-demo.
3. intake: accepted
   - Interface: `TodoService.list(*, done, search)` in `src/app/service/todo_service.py` and `list_todos` in `src/app/api/routes.py` are concrete and fit the current code. `MAX_TITLE_LENGTH` exists in `app.domain.model` (200). Every rule is stated: strip, `casefold` substring, `None` or blank means no filter, combine with `done`, repository order, 200-character limit counted as sent.
   - Criteria: each is testable by one test function without further decisions. Every Interface behaviour has a criterion (match and order 1 and 6, strip 2, None/empty/blank 3, casefold 4, combination with both `done` values 5 and 7, unfiltered listing 9). The limit has both sides (8): 200 gives 200 and `[]`, 201 gives 422, and the padded 197 spaces plus `milk` gives 422. The 422 body is checkable (`detail` only, starting with `query.search: `, matching the joined location in `app.api.errors`). Criteria 10 and 11 cover openapi and `make check`; no existing test is changed.
   - Smoke test: runnable (`build_app({})` exists, in-memory storage); the `Expect:` line is concrete: `['Buy Milk', 'MILK run']`, then `422 ['detail']`.
   - Architecture: the service filters `list_all()` and touches no repository or domain code; the API only passes the parameter and the existing handler maps the validation error. This is consistent with the layers in `CLAUDE.md`.
   - Scope: within F0003's scope (title search in the service and as a query parameter); no index, repository method, ranking or fuzzy matching. The feature's decisions 1 to 4 are all covered by criteria.
4. factory: started tests as opencode-demo.
5. tester: Wrote tests for criteria 1–9 against the Interface; criteria 10–12 are checked by the existing openapi test, `make check` and the docs stage, so they get no new test.

   - criterion 1: tests/service/test_search.py::test_search_returns_the_todos_whose_title_contains_the_text_in_creation_order
   - criterion 2: tests/service/test_search.py::test_search_text_is_stripped
   - criterion 3: tests/service/test_search.py::test_no_or_blank_search_means_no_title_filter (rows none, empty, spaces)
   - criterion 4: tests/service/test_search.py::test_search_uses_case_folding
   - criterion 5: tests/service/test_search.py::test_search_combines_with_the_done_filter (rows open, done)
   - criterion 6: tests/api/test_search.py::test_search_returns_the_matching_todos_in_creation_order
   - criterion 7: tests/api/test_search.py::test_search_combines_with_the_done_filter
   - criterion 8: tests/api/test_search.py::test_search_length_is_limited_on_the_text_as_sent (rows 200-chars, 201-chars, 201-chars-padded)
   - criterion 9: tests/api/test_search.py::test_list_without_parameters_returns_every_todo
   - criterion 10: existing tests/api/test_openapi.py::test_committed_schema_matches_the_app, unchanged

   Files created: tests/service/test_search.py, tests/api/test_search.py, tests/responses.py.
   Earlier test file changed: tests/api/test_todos.py. Under the standing leave in CLAUDE.md (*Tests*) I moved its private helper `_assert_only_detail` to tests/responses.py as `assert_only_detail`, because the new API test would otherwise have copied it. Every test in test_todos.py keeps its name and checks the same thing.

   Setup in the API tests goes through the `TodoService` handed to `create_app`, as test_todos.py::test_routes_use_the_service_given_to_create_app does, so the `_create`/`_complete` HTTP helpers are not copied.

   Modules not importable: none. Every module imports; the tests fail because `TodoService.list` does not take `search` yet (TypeError in the service tests) and because the route ignores `search` (wrong result or status in the API tests).

   Still green before implementation: criterion 7's test, because on the data the criterion gives `Buy Milk` is the only done todo, so `done=true` alone already returns it; and criterion 9's test, which checks the existing unfiltered listing. `make lint` is green. I skipped the type check, as this stage says to.

   `lint`: lint: green (0.0 s)
   `test`: 12 failed, 175 passed, 20 warnings in 4.30s
6. factory: started doing as opencode-demo.
7. coder: Implemented title search against the tester's tests. I changed no tests.

   What I built:
   - `src/app/service/todo_service.py`: `TodoService.list(*, done=None, search=None)` takes the repository's list and filters it in two steps. If `done` is given, it keeps only todos with that flag. It then strips `search` and applies `str.casefold`; if anything is left, it keeps only todos whose casefolded title contains that text. Creation order is unchanged. The docstring now covers both filters.
   - `src/app/api/routes.py`: `list_todos` takes `search: Annotated[str | None, Query(max_length=MAX_TITLE_LENGTH)] = None`, with `MAX_TITLE_LENGTH` imported from `app.domain.model`, and passes it to the service. The schema checks the limit on the text as sent, so a search over 200 characters gets a 422. The existing handler in `app.api.errors` produces the `query.search: ...` detail.
   - `docs/openapi.json`: regenerated with `make openapi`.

   Main decision: the service narrows one list step by step, so `None`, an empty search and a blank search all go through the same "no title filter" path. The alternative I rejected was a single list comprehension with one condition for `done` and one for search. It saves a pass over the list, but it is harder to read, and the lists are small.

   Refactor pass: I read the diff once more and found nothing to change.

   Noticed, not touched: pytest prints a `StarletteDeprecationWarning` about `httpx` in `fastapi.testclient`. It comes from the installed dependencies and was there before this change. Criterion 12 (the docs) belongs to the documenter.

   make check: check: green (187 passed).

   `check`: check: green
   `duplicates`: duplicates: 0 similar code, 8 dead code, in .reports/
8. factory: started review as opencode-demo.
9. reviewer: Reviewed `git diff main...HEAD -- . ':!factory'` (I skipped `docs/openapi.json`) against the work item.

   The source changes are fine. `TodoService.list` strips `search`, applies `casefold` to both sides and filters after `done`, keeping the repository's order. `list_todos` declares `Query(max_length=MAX_TITLE_LENGTH)` and passes `search` on. The layers hold, and the service docstring is current.

   Every criterion from 1 to 9 has a test that checks what the criterion says. The length limit is tested on both sides, including the padded case, as rows of one parametrized test. The coder's journal entry reports `make check` green.

   Main point: this is round 0, so copies of existing test helpers count as findings, and the new test files copy three fixtures.

   Findings:
   1. tests/api/test_search.py:13-20: the `service` and `client` fixtures are copies of tests/api/test_todos.py:24-31, and `service` is also in tests/api/test_stats.py:15-17. Fix: under the standing leave, move `service` (built with `TickingClock`) and `client` into tests/conftest.py and use them from there in the earlier modules and the new one.
   2. tests/service/test_search.py:11-13: the `service` fixture copies `ticking_service` in tests/service/test_todo_service.py:23-25. Fix: reuse the shared fixture from finding 1 instead of a second copy.
   3. tests/service/test_search.py:21-25 and tests/api/test_search.py:28-32: the same `milk_done_and_open` fixture is written twice. Fix: define it once in tests/conftest.py. Do the same for the three-title setup (`three_todos` and `three_ids`) if one shared fixture can return the created todos.

   Earlier tests:
   - tests/api/test_todos.py: changed under the standing leave to move a shared test helper. Only `_assert_only_detail` was moved, to tests/responses.py as `assert_only_detail`. Every test keeps its name and checks the same thing.
10. factory: started doing as opencode-demo.
11. coder: Round 1. All three review findings are about test fixtures copied between test files, so they are test changes. `CLAUDE.md` (*Tests*) gives the tester a standing leave to move them; the coder does not. I changed no code and no tests. The source the reviewer accepted is unchanged: `src/app/service/todo_service.py`, `src/app/api/routes.py`, `docs/openapi.json`.

    Moves for the tester, under the standing leave:
    1. Move the `service` fixture (built with `TickingClock`) and the `client` fixture into `tests/conftest.py`. They are copied in `tests/api/test_search.py`, `tests/api/test_todos.py` and `tests/api/test_stats.py`; change all three to use the shared ones. `tests/api/test_health.py` also has a `service` fixture: check whether it is the same and include it if so.
    2. Replace the `service` fixture in `tests/service/test_search.py` with the shared fixture from move 1. That fixture is the same as `ticking_service` in `tests/service/test_todo_service.py`, so change that module to use the shared one too, keeping its test names.
    3. Define `milk_done_and_open` once in `tests/conftest.py`; it is now in both `tests/service/test_search.py` and `tests/api/test_search.py`. If one shared fixture can return the created todos, do the same for the three-title setup (`three_todos` in the service test, `three_ids` in the API test).

    Every earlier test must keep its name and check the same thing. The tester's entry names each earlier test file it changes.

    Main decision: hand back with `tests` and leave the fixtures alone. Rejected alternative: moving them myself. The coder never edits tests, not even under the standing leave.

    Description: unchanged. The journal changed no meaning of the task.

    Noticed, not touched: as in round 0, pytest's `StarletteDeprecationWarning` from `fastapi.testclient`, which comes from the installed dependencies. Criterion 12 (docs) is the documenter's.
