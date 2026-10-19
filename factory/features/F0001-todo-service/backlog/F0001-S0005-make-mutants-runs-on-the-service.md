# Make mutants runs on the service module

<!-- proposed by feature acceptance of 2026-10-19; refine before starting -->

## Description

`make mutants FEATURE=F0001` stops before it tests a single mutant: pytest cannot import mutmut's rewritten `app.service.todo_service`. mutmut adds its generated methods to the body of `TodoService` after the method `list`, and each copy of `list` carries the annotation `-> list[Todo]`. Inside the class body, the name `list` now means the method, so `list[Todo]` raises `TypeError: 'function' object is not subscriptable`. S0002's coder noted this risk ("any later method in the class that needs a `list[...]` annotation would run into this"). This story keeps the public method name `list`, so the routes, the tests and the documentation stay as they are. It spells the built-in type `builtins.list` in the service module wherever the name could be shadowed, so the mutation report runs again. Behaviour does not change. Renaming the method instead (for example to `list_todos`) is the alternative: it would change S0002's Interface and its tests, which needs the human's leave.

## Interface

`src/app/service/todo_service.py`

```python
import builtins

class TodoService:
    def list(self, *, done: bool | None = None) -> builtins.list[Todo]: ...
```

- Every annotation in the class body of `TodoService` that names the built-in list type spells it `builtins.list`, never the bare name `list`.
- No signature, behaviour or docstring of `TodoService` changes otherwise.

Tests: `tests/service/test_annotations.py` (new). It parses the service module with `ast` and names only what must not appear: a bare `list` name in an annotation inside `TodoService`. No earlier test changes.

## Acceptance criteria

1. No annotation in the body of class `TodoService` in `src/app/service/todo_service.py` (argument, return or variable annotation) contains the bare name `list` as a `Name` node. The test fails on the module as it is today, where `list`'s own return annotation is `list[Todo]`.
2. `typing.get_type_hints(TodoService.list)["return"]` equals `list[Todo]` (the built-in), so the type the method promises is unchanged.
3. `make check` stays green.
4. docs: `docs/project-guide.md`, *Service*: one sentence saying that the method name `list` shadows the built-in inside the class body, so the module spells the type `builtins.list` there.

## Smoke test

```bash
make mutants FEATURE=F0001 2>&1 | tail -3
```

Expect: the last line is `mutants: green (<seconds> s)`, and no line before it holds `TypeError: 'function' object is not subscriptable`.

```bash
uv run python -c "
import typing
from app.service.todo_service import TodoService
print(typing.get_type_hints(TodoService.list)['return'])
"
```

Expect: one line, `list[app.domain.model.Todo]`.

## Journal
