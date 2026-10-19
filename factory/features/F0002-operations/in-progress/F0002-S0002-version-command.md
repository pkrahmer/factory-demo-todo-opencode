---
stage: doing
blocked: null
round: 1
attempts: 0
crashes: 0
pull_request: 7
comments_read: []
handed_over: null
claim: null
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
- number: 7
  speaker: tester
  kind: result
  at: '2026-10-19T13:41:14.428596Z'
  stage: tests
  run: 9331f7b86f274ce896764cd218ddd653
- number: 8
  speaker: factory
  kind: started
  at: '2026-10-19T13:41:35.289108Z'
  stage: doing
- number: 9
  speaker: coder
  kind: result
  at: '2026-10-19T13:42:19.057491Z'
  stage: doing
  run: 58d2dd1e98e3490fa0ef838764a0f851
- number: 10
  speaker: factory
  kind: started
  at: '2026-10-19T13:42:39.098641Z'
  stage: review
- number: 11
  speaker: reviewer
  kind: result
  at: '2026-10-19T13:43:10.669238Z'
  stage: review
  run: 101e240662f649aabed2fb63f0c8f363
- number: 12
  speaker: factory
  kind: started
  at: '2026-10-19T13:43:31.534513Z'
  stage: doing
- number: 13
  speaker: coder
  kind: result
  at: '2026-10-19T13:43:44.302994Z'
  stage: doing
  run: 11e2cbe7da7a40f68a5cdd4d9b107281
- number: 14
  speaker: factory
  kind: started
  at: '2026-10-19T13:44:04.823884Z'
  stage: tests
- number: 15
  speaker: tester
  kind: result
  at: '2026-10-19T13:44:51.989267Z'
  stage: tests
  run: c38a0d3ec2fb413aa445fd1fe050cf42
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
7. tester: I wrote the tests for criteria 1–5 in a new file, `tests/test_main.py`, against the Interface of `src/app/__main__.py`. They call `main` and capture its output with `capsys`. Criterion 4 reuses the existing helper `tests/imports.py` (`APP_DIR`, `imported_modules`) and names only the forbidden layers. Criterion 5 runs the module as a child process with `sys.executable`. The expected version line is `f"app {importlib.metadata.version('app')}\n"`.

   - criterion 1: tests/test_main.py::test_version_flag_prints_the_installed_version
   - criterion 2: tests/test_main.py::test_any_other_arguments_are_a_usage_error (rows: [], ["--help"], ["x"], ["--version", "x"])
   - criterion 3: tests/test_main.py::test_main_without_argument_reads_sys_argv (rows: ["app", "--version"] → 0, ["app"] → 2)
   - criterion 4: tests/test_main.py::test_entry_point_imports_no_layer
   - criterion 5: tests/test_main.py::test_running_the_module_as_a_child_process (rows: --version → 0 with the version line on stdout and an empty stderr; no argument → 2 with an empty stdout and the usage line on stderr)
   - criterion 6 (`make check`) and criterion 7 (docs) have no test of their own.

   Files created: tests/test_main.py. No earlier test file was changed.

   Module the test runner could not import: `app.__main__`, which does not exist yet. `make test` stops with an ImportError while collecting tests/test_main.py. All 155 existing tests pass. `make lint` is green. I did not have to interpret any criterion, so there is no open question.

   `lint`: lint: green (0.0 s)
   `test`: 155 passed, 20 warnings, 1 error in 6.79s
8. factory: started doing as opencode-demo.
9. coder: What I built: `src/app/__main__.py`. It holds `main(argv: list[str] | None = None) -> int` and the `sys.exit(main())` guard. With no `argv` given, `main` reads `sys.argv[1:]`. The argument list `["--version"]` prints `app {importlib.metadata.version('app')}` to stdout and returns 0. Every other argument list prints `usage: python -m app --version` to stderr and returns 2. The module imports only `sys` and `importlib.metadata`, nothing from the layers. The usage line and the two exit codes are named module constants.

   Main choice: one exact comparison, `arguments != ["--version"]`, instead of `argparse`. I rejected `argparse` for three reasons:
   - it adds its own `--help` with exit 0;
   - its usage text is different;
   - it exits through `SystemExit`, where the Interface wants a returned 2 and a fixed usage line for every other argument list.

   Refactor: I read the diff and nothing needed changing. The tests in `tests/test_main.py` were not touched.

   `make check`: green, 165 passed.

   Noticed, not touched:
   - Coverage reports line 21 of `__main__.py`, the `sys.exit(main())` guard, as not covered. The child-process test does run it, but the child is outside coverage's measurement. Total coverage is 99.38%, above the 90% gate.
   - The docs criterion, the README's *Getting started* section, is the documenter's.

   `check`: check: green
   `duplicates`: duplicates: 0 similar code, 7 dead code, in .reports/
10. factory: started review as opencode-demo.
11. reviewer: Findings:
    1. tests/test_main.py:57 (`test_entry_point_imports_no_layer`): the inline check `module == layer or module.startswith(f"{layer}.")` is a third copy of a check that already exists as `_is_repository` in tests/api/test_imports.py and inside `_is_forbidden` in tests/domain/test_imports.py. Fix: the tester adds one shared function, e.g. `belongs_to(module: str, package: str) -> bool`, to tests/imports.py and uses it in test_main.py. Under the standing leave to move a shared test helper, the tester may also make `_is_repository` and `_is_forbidden` use it, as long as each earlier test keeps its name and checks the same thing.

    What I checked:
    - Criteria 1 to 5: each test checks its criterion exactly: the streams, the exact text with its newline, the return or exit code. Criterion 2's four usage-error cases are rows of one parametrized test. Criterion 3 covers both of its cases. Criterion 5 runs the module as a child process with `sys.executable` and covers both its cases. The coder's journal entry 9 reports `make check` green.
    - Architecture: src/app/__main__.py imports only `sys` and `importlib.metadata`, nothing from the layers, and adds no new package or dependency.
    - Security: no secrets, no strings built into shell commands, no markers that silence a check.
    - Code quality in src/: the names say what things are, there is no dead code, and the module docstring is present, which is all `CLAUDE.md` asks of `__main__`.
    - Work item: the Description matches what was built. The journal explains why the coder rejected `argparse`. The docs criterion still says what the README must show.

    Earlier tests: none. The diff changes, renames or deletes no test file that `main` already holds; it only adds tests/test_main.py.
12. factory: started doing as opencode-demo.
13. coder: I changed no code and no tests this round. The one review finding (entry 11) is a test change, and `CLAUDE.md` gives a standing leave to move a shared test helper, so the tester makes it.

    What I built: nothing new this round. `src/app/__main__.py` is unchanged since entry 9.

    Test change requested:
    - Add one shared function to `tests/imports.py`, for example `belongs_to(module: str, package: str) -> bool`, which returns `module == package or module.startswith(f"{package}.")`.
    - Use it in `tests/test_main.py::test_entry_point_imports_no_layer` in place of the inline check at line 57.
    - Under the same leave, make `_is_repository` in `tests/api/test_imports.py` and `_is_forbidden` in `tests/domain/test_imports.py` use it too. Each earlier test keeps its name and checks the same thing. The tester's entry names each earlier test file it changed.

    Main choice: I handed the finding to the tester instead of answering it in code, because the coder never edits tests. I rejected asking the human, because the standing leave covers this move.

    Description: unchanged. The journal did not change what the task means.

    Noticed, not touched: the docs criterion (the README's *Getting started* section) is the documenter's.
14. factory: started tests as opencode-demo.
15. tester: I made the test change from the coder's entry 13. It answers the review finding in entry 11, under the standing leave in `CLAUDE.md` to move a shared test helper, so it did not need the human's word.

    - Added `belongs_to(module: str, package: str) -> bool` to `tests/imports.py`. It returns `module == package or module.startswith(f"{package}.")`.
    - `tests/test_main.py::test_entry_point_imports_no_layer` now uses `belongs_to` in place of the inline check.
    - Earlier test file changed: `tests/api/test_imports.py`. `_is_repository` now returns `belongs_to(module, "app.repository")`. `test_only_main_imports_the_repository_layer` keeps its name and checks the same thing.
    - Earlier test file changed: `tests/domain/test_imports.py`. In `_is_forbidden`, `outside_domain` is now `not belongs_to(module, "app.domain")`. `test_domain_imports_no_framework_and_no_outer_layer` keeps its name and checks the same thing.

    The criterion-to-test mapping is unchanged from entry 7:
    - criterion 1: tests/test_main.py::test_version_flag_prints_the_installed_version
    - criterion 2: tests/test_main.py::test_any_other_arguments_are_a_usage_error
    - criterion 3: tests/test_main.py::test_main_without_argument_reads_sys_argv
    - criterion 4: tests/test_main.py::test_entry_point_imports_no_layer
    - criterion 5: tests/test_main.py::test_running_the_module_as_a_child_process

    I created no files. No module failed to import, because `app.__main__` exists now. `make test`: 165 passed. `make lint`: green.

    `lint`: lint: green (0.0 s)
    `test`: test: green (7.2 s)
