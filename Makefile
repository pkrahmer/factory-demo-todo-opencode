# The contract between a project and the factory is three targets: `check`, `lint`, `test`.
# `check` is what every stage must pass; `lint` and `test` are what the tests stage runs on its
# own (the type check is skipped there, because the modules under test do not exist yet).
# `duplicates` and `mutants` are reports outside `check`; `openapi` writes docs/openapi.json.
#
# The development dependencies the targets need, pinned in pyproject.toml: ruff, mypy, semgrep,
# bandit, detect-secrets, pip-licenses, pytest, pytest-cov, pytest-xdist, pylint, vulture,
# mutmut, and the tool of the layers command (import-linter for `uv run lint-imports`).
# pyproject.toml configures them (coverage's `source` and `fail_under`, mypy's `strict`, and
# `[tool.mutmut]`, which copies docs/ beside the mutated source); security/semgrep holds
# the vendored semgrep rules and .secrets.baseline the reviewed findings of detect-secrets.
.PHONY: check lint types layers sast secrets licenses test duplicates mutants openapi
.SILENT:

# What the project decides: the folder of its package, and the command that checks its layers.
SOURCE = src/app
LAYERS = uv run lint-imports

# One shell per recipe, stopped by its first failing line, so that a recipe can time itself.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:

# `$(start)` opens a recipe and `$(green)` ends it with "<target>: green (<seconds> s)",
# the line the factory's records of project commands read.
start = started=$$(date +%s%N)
green = tenths=$$(( ($$(date +%s%N) - started) / 100000000 )); echo "$@: green ($$((tenths / 10)).$$((tenths % 10)) s)"

check: lint types layers sast secrets licenses test
	echo "check: green"

lint:
	$(start)
	uv run ruff check --output-format=concise .
	uv run ruff format --check --quiet .
	$(green)

types:
	$(start)
	uv run mypy
	$(green)

layers:
	$(start)
	$(LAYERS)
	$(green)

# Static analysis: semgrep with rule sets vendored under security/semgrep (copy the sets you
# want from github.com/semgrep/semgrep-rules; offline and pinned), plus bandit.
sast:
	$(start)
	SEMGREP_SEND_METRICS=off uv run semgrep scan --config security/semgrep --metrics=off \
	  --disable-version-check --quiet --error $(SOURCE)
	uv run bandit -q -r $(SOURCE)
	$(green)

# Secrets beyond the reviewed baseline, in the files changed against origin/main (committed,
# staged, unstaged or new); every tracked file on main itself or without origin/main.
secrets:
	$(start)
	if [ "$$(git rev-parse HEAD)" != "$$(git rev-parse --verify --quiet origin/main || true)" ] && base=$$(git merge-base HEAD origin/main 2>/dev/null); then
	  files=$$( { git diff --name-only --diff-filter=d "$$base"; git ls-files --others --exclude-standard; } | sort -u)
	else
	  files=$$(git ls-files)
	fi
	files=$$(printf '%s\n' $$files | grep -vE '^(uv\.lock|\.secrets\.baseline|.*\.costs\.jsonl)$$' || true)
	if [ -n "$$files" ]; then uv run detect-secrets-hook --baseline .secrets.baseline $$files; fi
	$(green)

# Licences of the production dependencies against an allow list.
ALLOWED_LICENSES = MIT;MIT License;MIT-0;BSD;BSD License;BSD-2-Clause;BSD-3-Clause;3-Clause BSD License;ISC;ISC License;Apache-2.0;Apache 2.0;Apache Software License;PSF-2.0;Python Software Foundation License;MPL-2.0;Mozilla Public License 2.0 (MPL 2.0);GNU Library or Lesser General Public License (LGPL);Apache-2.0 OR BSD-3-Clause
licenses:
	$(start)
	mkdir -p .reports
	uv export -q --frozen --no-dev --no-emit-project --format requirements-txt -o .reports/licenses-requirements.txt
	uv run pip-licenses --from=mixed --allow-only="$(ALLOWED_LICENSES)" \
	  --packages $$(sed -n 's/^\([A-Za-z0-9_.-]*\)==.*/\1/p' .reports/licenses-requirements.txt) > /dev/null
	rm -f .reports/licenses-requirements.txt
	$(green)

# Every core (pytest-xdist), short tracebacks, no banner; coverage as pyproject.toml sets it,
# with the lines that miss; the time of every test in the JUnit report .reports/junit.xml.
# Exit status 5 is pytest's "no tests collected": green for the empty project, impossible
# once the first test exists.
test:
	$(start)
	mkdir -p .reports
	uv run pytest -q --no-header --tb=short -p no:cacheprovider -n auto --dist load \
	  --junit-xml=.reports/junit.xml --cov --cov-report=term-missing:skip-covered || [ $$? -eq 5 ]
	$(green)

# Similar code (pylint's duplicate-code) and dead code (vulture) in the package, written to
# .reports/ and counted on the last line, which a report records; never a failure for its findings.
duplicates:
	mkdir -p .reports
	uv run pylint --disable=all --enable=duplicate-code --output-format=json --exit-zero $(SOURCE) > .reports/similar-code.json
	uv run vulture $(SOURCE) --min-confidence 60 > .reports/dead-code.txt || [ $$? -eq 3 ]
	similar=$$(grep -c '"symbol": "duplicate-code"' .reports/similar-code.json || true)
	dead=$$(wc -l < .reports/dead-code.txt)
	echo "duplicates: $$similar similar code, $$dead dead code, in .reports/"

# Mutation testing of the modules of the package that one feature's stories changed:
# `make mutants FEATURE=F0001`. Slow, so not part of `check`; the feature acceptance runs it,
# and on an acceptance's branch (work-item/<feature id>-A<number>) FEATURE is that feature. A story's
# commits are those whose subject starts `work item <id>:`, or `<id>:` after a squash merge.
FEATURE ?= $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null | sed -n 's|^work-item/\(F[0-9]\{4\}\)-A[0-9]\{4\}$$|\1|p')
MUTATED = $(wildcard $(shell git log --format= --name-only -E --grep='^(work item )?$(FEATURE)-S[0-9]{4}([: ]|$$)' origin/main -- '$(SOURCE)/*.py' 2>/dev/null | sort -u))
mutants:
	$(start)
	if [ -z "$(FEATURE)" ]; then echo "mutants: set FEATURE, as in make mutants FEATURE=F0001"; exit 2; fi
	if [ -z "$(MUTATED)" ]; then echo "mutants: no module under $(SOURCE) changed by $(FEATURE)"; exit 0; fi
	uv run mutmut run $(foreach module,$(MUTATED),"$(subst /,.,$(patsubst src/%.py,%,$(module))).*")
	# mutmut generates mutants for every module; the ones outside the feature stay "not checked".
	uv run mutmut results | { grep -v ': not checked$$' || true; }
	$(green)

# docs/openapi.json is the API schema as the running app reports it, committed so it can be
# read on GitHub. A test fails when it is stale; the coder runs this after changing a route or
# a schema.
openapi:
	$(start)
	mkdir -p docs
	uv run python -c "import json; from app.api.main import app; print(json.dumps(app.openapi(), indent=2, sort_keys=True))" > docs/openapi.json
	$(green)
