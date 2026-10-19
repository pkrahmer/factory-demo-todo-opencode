---
stage: tests
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: 10
comments_read: []
handed_over: null
claim:
  instance: opencode-demo
  stage: tests
  started_at: '2026-10-19T14:04:28.569051Z'
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
