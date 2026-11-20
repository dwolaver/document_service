# Design

## Context

`pyproject.toml` defines the package and its commands, with no tool configuration. `pytest.ini`
configures pytest. `requirements-dev.txt` holds `-r requirements.txt`, `-e .` and a pinned
`pytest`. `.github/workflows/ci.yml` has one job, `test`, which installs `requirements-dev.txt` on
Python 3.14 and runs `pytest`. `.gitignore` already ignores `.ruff_cache/` and `.mypy_cache/`.

The current code, with the planned settings (measured with ruff 0.17.6 and mypy 2.4.1):

- `ruff format` would change 15 of 25 Python files, about 229 lines.
- The lint rules find two problems, both in tests: `l` as a variable name in
  `tests/ingestion/test_rfc_parser.py` (E741), and a lambda assigned to a name in
  `tests/test_paths.py` (E731). Import sorting finds nothing.
- mypy finds one error: `ROOT_MODULE_ALLOW_LIST = set()` in `tests/test_packaging.py` needs an
  annotation. Checking `scripts/` and `tests/` together also needs `explicit_package_bases`, because
  `scripts/update_architecture.py` is otherwise found under two module names.

## Goals / Non-Goals

**Goals:**
- One definition of each check, used by the hook and by CI.
- One pinned version of each tool, in `requirements-dev.txt`.
- A clean starting point: every check passes on `main` once this change merges.

**Non-Goals:**
- Fixing problems automatically in the hook. The hooks only report, and the README gives the
  commands that fix.
- A blame-ignore file for the reformat commit. Pull requests are squash-merged, so the reformat's
  commit on the branch won't exist on `main`.

## Decisions

### Configuration in `pyproject.toml`

```toml
[tool.ruff]
line-length = 110
include = ["*.py"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "B"]

[tool.mypy]
files = ["rfc_qa", "scripts", "tests"]
explicit_package_bases = true
warn_unused_configs = true
```

The rules are listed with `select`, not added with `extend-select`, because ruff 0.17's default set
is much broader than pyflakes and pycodestyle errors. It includes pyupgrade and simplify, which were
left out of scope, and it changes between releases. Listing the rules keeps the set fixed until a
change edits it.

`include` limits ruff to Python files. By default ruff 0.17 also formats Python code blocks in
Markdown, which would reach the archived OpenSpec records and the README.

ruff reads `requires-python` for its target version, so no `target-version` is set. mypy runs at its
defaults otherwise.

The 110-character limit changes the fewest lines: about 229 at 110, against about 404 at 100. 120
changes about the same as 110 but allows longer lines than the code has today.

Alternative: separate `ruff.toml` and `mypy.ini` files. Rejected because `pyproject.toml` already
exists, and both tools read it.

### Hooks run the tools from the project's environment

`.pre-commit-config.yaml` defines three `repo: local` hooks, with `language: system`:

| id | entry | runs on |
|---|---|---|
| `ruff-check` | `ruff check` | Python files being committed |
| `ruff-format` | `ruff format --check` | Python files being committed |
| `mypy` | `mypy` | the whole project (`pass_filenames: false`, `types: [python]`) |

mypy checks the whole project rather than the changed files, so that a change in one module that
breaks a caller in another is caught.

`requirements-dev.txt` pins `ruff`, `mypy`, `types-requests` and `pre-commit`.

Alternative: the published hook repositories (`astral-sh/ruff-pre-commit`, `mirrors-mypy`), which
install each tool in pre-commit's own environment. Rejected because each tool would then be pinned in
two places, which could drift. mypy would also need the project's dependencies listed again as
`additional_dependencies` to check calls into `requests` and `pytest`. The cost of local hooks is that
the hook needs the project's virtual environment active, which the README already says to set up.

### CI runs the hooks

A `quality` job in `ci.yml`, beside `test`, installs `requirements-dev.txt` on Python 3.14 and runs
`pre-commit run --all-files`. Running the hooks keeps the commands in one
place. Any change to a hook changes CI too.

A separate job, rather than a step in `test`, so that a pull request shows formatting and test
failures separately, and one doesn't hide the other.

Making `quality` a required check for `main` is a repository setting, which only the owner can
change. It can be set once the job has run on this change's pull request, before merging.

### One reformat, then the fixes

The reformat is done once with `ruff format`, with no hand edits, so that the diff can be reviewed as
purely mechanical. The two lint findings and the mypy finding are fixed by hand, after the reformat.

ruff formats for Python 3.14, so it removes the parentheses from `except (TypeError, ValueError):`,
producing `except TypeError, ValueError:` (PEP 758). That's valid on the project's only supported
version, and is accepted as the formatter's choice rather than overridden.

## Risks / Trade-offs

- [The hook fails with "command not found" when the virtual environment isn't active] → The README
  says to activate it before committing. CI catches anything the hook missed.
- [`except A, B:` reads like Python 2's `except A, e:`] → Python 3.14 parses it as a tuple of
  exception types, and ruff only writes it when the target version allows it. Reviewers see the two
  instances in the reformat diff.
- [Open pull requests conflict with the reformat] → None are open. Future branches start from the
  formatted code.

## Migration Plan

All in one pull request. After it merges, each developer runs `pip install -r requirements-dev.txt`
and `pre-commit install` once. The owner adds `quality` to the required checks. To roll back, revert
the commit and remove the required check.
