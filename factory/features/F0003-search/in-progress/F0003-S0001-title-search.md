---
stage: review
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 10
comments_read: []
handed_over: null
claim:
  instance: opencode-demo
  stage: review
  started_at: '2026-10-19T14:07:30.096430Z'
  lease_duration: 60
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
