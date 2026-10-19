---
stage: intake
blocked: null
round: 0
attempts: 0
crashes: 0
pull_request: null
comments_read: []
handed_over: null
claim:
  instance: opencode-demo
  stage: intake
  started_at: '2026-10-19T13:38:21.085124Z'
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
