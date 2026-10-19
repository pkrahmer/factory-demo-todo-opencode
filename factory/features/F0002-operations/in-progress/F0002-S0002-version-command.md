---
stage: tests
blocked: null
round: 0
attempts: 0
crashes: 1
pull_request: 7
comments_read: []
handed_over: null
claim:
  instance: opencode-demo
  stage: tests
  started_at: '2026-10-19T13:40:23.589192Z'
  lease_duration: 60
journal:
- number: 1
  speaker: human
  kind: created
  at: '2026-10-19T13:38:21.078857Z'
  stage: intake
- number: 2
  speaker: factory
  kind: started
  at: '2026-10-19T13:38:21.085124Z'
  stage: intake
- number: 3
  speaker: intake
  kind: result
  at: '2026-10-19T13:38:43.690691Z'
  stage: intake
  run: 63fc321dfb3c481f9390f7304eae1302
- number: 4
  speaker: factory
  kind: started
  at: '2026-10-19T13:39:03.810577Z'
  stage: tests
- number: 5
  speaker: factory
  kind: crash
  at: '2026-10-19T13:40:21.531288Z'
  stage: tests
- number: 6
  speaker: factory
  kind: started
  at: '2026-10-19T13:40:23.589192Z'
  stage: tests
---

# Version command

## Description

Let support ask a machine which version is installed without starting the server: `uv run python -m app --version` prints `app <version>` and exits 0. The module is a small command-line entry point that knows nothing of the layers below it.

## Interface

`src/app/__main__.py`

```python
def main(argv: list[str] | None = None) -> int: ...
# argv defaults to sys.argv[1:]
# ["--version"]: prints "app <version>" to stdout (importlib.metadata.version("app")), returns 0
# []: prints "usage: python -m app --version" to stderr, nothing to stdout, returns 2
# anything else: like [], returns 2

if __name__ == "__main__":
    sys.exit(main())
```

Tests: `tests/test_main.py` (the module is outside the layers), calling `main` with `capsys`, and running the module as a child process with the interpreter that runs the tests.

## Acceptance criteria

1. `main(["--version"])` writes exactly `app <version>` and a newline to stdout, where `<version>` is `importlib.metadata.version("app")`, writes nothing to stderr, and returns 0.
2. Every other argument list is a usage error, as rows of one parametrized test: `main([])`, `main(["--help"])`, `main(["x"])` and `main(["--version", "x"])` each return 2, write nothing to stdout, and write `usage: python -m app --version` and a newline to stderr.
3. `main()` without an argument reads `sys.argv[1:]`: with `sys.argv` set to `["app", "--version"]` it returns 0, and with `["app"]` it returns 2.
4. `app.__main__` imports nothing from `app.domain`, `app.service`, `app.repository` or `app.api` (a test that parses its imports and names only these forbidden ones).
5. Run as a module, as rows of one parametrized test: `subprocess.run([sys.executable, "-m", "app", "--version"], capture_output=True, text=True, check=False)` exits 0 with stdout `app <version>` and a newline and an empty stderr; without an argument it exits 2 with an empty stdout and stderr `usage: python -m app --version` and a newline.
6. `make check` stays green.
7. docs: the README's *Getting started* shows `uv run python -m app --version` and what it prints.

## Smoke test

```bash
uv run python -m app --version; echo "exit $?"
```

Expect: two lines, `app 0.1.0`, then `exit 0`.

```bash
uv run python -m app; echo "exit $?"
```

Expect: two lines, `usage: python -m app --version` (on stderr), then `exit 2`.

## Journal

1. 2026-10-19 human: created.
2. factory: started intake as opencode-demo.
3. intake: accepted
   - Interface: `src/app/__main__.py` is not built yet. It names one concrete function, `main(argv: list[str] | None = None) -> int`, with the `argv` default (`sys.argv[1:]`), the output stream and the return value for each case, and the `sys.exit(main())` guard. The version source `importlib.metadata.version("app")` matches `pyproject.toml` (name `app`, version `0.1.0`) and the existing `app/api/health.py`.
   - Criteria: every Interface behaviour has its own criterion, and the failing side is covered too.
     - Criterion 1 covers `--version` (stdout text, empty stderr, return 0).
     - Criterion 2 covers `[]`, `--help`, `x` and `--version x` as rows of one parametrized test (return 2, empty stdout, usage line on stderr).
     - Criterion 3 covers the `argv` default from `sys.argv` in both branches.
     - Criterion 4 covers the "knows nothing of the layers" claim, and names only the forbidden imports.
     - Criterion 5 covers the same cases as a child process with `sys.executable`.
     - Each criterion is testable by one test function, or one parametrized test, without further decisions.
   - Smoke test: both commands are runnable (`uv run python -m app --version` and `uv run python -m app`, each with `echo "exit $?"`). Each `Expect:` line is checkable: exact lines, stream named, exit code given. The `0.1.0` matches `pyproject.toml`.
   - Architecture: `app.__main__` is a module outside the layers and is tested at the `tests/` root, as `CLAUDE.md` says. It needs nothing from `app.domain`, `app.service`, `app.repository` or `app.api`, and the story says so. It is wired by hand without a new dependency (`argparse` is not required), and it adds no new top-level package. The existing `tests/imports.py` helper is available for criterion 4. The docs criterion targets the README's *Getting started* section, which exists.
   - Scope: this is the feature's Scope item `python -m app --version` and is not in its Out of scope. It matches the feature's decisions 2, 5 and 8 (usage error for any other argument, exact `--version` only, child-process test).
   No questions. No story edits.
4. factory: started tests as opencode-demo.
5. factory: crash 1: the run of stage tests ended without a result. Its work is discarded back to commit 6c4ee3a92d80aabcc2e3378ed64fc7cef8f041e8.
6. factory: started tests as opencode-demo.
