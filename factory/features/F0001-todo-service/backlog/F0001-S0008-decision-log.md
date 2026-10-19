# Decision log and links that resolve

<!-- proposed by feature acceptance of 2026-10-19; refine before starting -->

## Description

`CLAUDE.md` names `docs/decisions.md` as the decision log, and the pipeline's rules cite lasting reasons from it, but the file does not exist. The documenters of S0001, S0002 and S0003 each noted the gap and left it. The lasting reasons of the feature live only in the archived stories' journals. These are:

- every rule sits in `Todo.__post_init__`;
- the done filter runs in the service, over `list_all()`;
- the error handlers are typed and registered with `app.exception_handler`;
- the service is passed to `create_app` and read back from `app.state`;
- `created_at` is stored in a fixed-width UTC text, so the database sorts;
- no repository inherits the protocol.

This story writes `docs/decisions.md` from those journals and from the decisions in `feature.md` that the human accepted with the feature. It adds a test that every `docs/<name>.md` the project's documents name exists, so a named document cannot go missing again. It also brings the README's intro up to date: the feature is complete, and "it is being built story by story" no longer describes it. No code changes.

## Interface

No production code.

- `docs/decisions.md` (new, by the documenter): one numbered entry per decision. Each entry has the decision, its reason, the alternative rejected, and where it was taken (story id).
- Tests: `tests/test_docs.py` (new). It reads `README.md`, `CLAUDE.md` and every `docs/*.md`, collects each path of the form `docs/<name>.md` they mention, and checks that each exists. It names no expected list.

## Acceptance criteria

1. Every path of the form `docs/<name>.md` named in `README.md`, `CLAUDE.md` or a `docs/*.md` file exists in the repository. The test fails today on `docs/decisions.md`, and a row per path makes a missing one visible by name.
2. The test has its failing side: given text naming `docs/missing.md` (a string in the test, not a file), the path-collecting helper returns it, and the existence check reports it as missing.
3. `make check` stays green.
4. docs: `docs/decisions.md` holds at least the six decisions this Description lists, each with its reason, the rejected alternative and its story. `README.md`'s *Where to look next* links it, and its intro no longer says the service is being built story by story.

## Smoke test

```bash
test -f docs/decisions.md && echo "decision log exists"
grep -c '^[0-9]\+\. ' docs/decisions.md
```

Expect: two lines, `decision log exists`, then a number of at least `6`.

```bash
uv run pytest -q -p no:cacheprovider tests/test_docs.py 2>&1 | tail -1
```

Expect: one line that starts with a number of tests and the word `passed`, with no `failed`.

## Journal
