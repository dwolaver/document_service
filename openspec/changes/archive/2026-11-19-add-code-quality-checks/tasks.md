# Tasks

## 1. Tools and configuration

- [x] 1.1 Pin the current releases of `ruff`, `mypy`, `types-requests` and `pre-commit` in `requirements-dev.txt`, and add the `[tool.ruff]`, `[tool.ruff.lint]` and `[tool.mypy]` tables from design.md to `pyproject.toml`; verify `pip install -r requirements-dev.txt` succeeds, `ruff --version` and `mypy --version` print the pinned versions, and `ruff check` and `mypy` run and report the findings listed in design.md (2 lint, 1 type), with no unknown-setting warnings

## 2. Clean up the existing code

- [x] 2.1 Run `ruff format` over the repository with no other edits; verify `ruff format --check` passes, `git diff --stat` touches only Python files, and `pytest` gives the same pass and skip counts as before the change
- [x] 2.2 Fix the lint findings by hand: rename `l` in `tests/ingestion/test_rfc_parser.py` and replace the assigned lambda in `tests/test_paths.py` with a `def`; verify `ruff check` passes and `pytest` gives the same counts
- [x] 2.3 Annotate `ROOT_MODULE_ALLOW_LIST` in `tests/test_packaging.py` as `set[str]`; verify `mypy` reports no issues and `pytest` gives the same counts

## 3. Pre-commit hook

- [x] 3.1 Add `.pre-commit-config.yaml` with the three local hooks from design.md (`ruff-check`, `ruff-format` running `ruff format --check`, and `mypy` over the whole project); verify `pre-commit run --all-files` passes, then in a scratch commit (reset afterwards) check that with the hook installed, a staged file with an unused import stops the commit and names the file and line, a staged file with bad formatting stops the commit and is left unchanged, and a clean file commits
- [x] 3.2 Document the checks in the README's "Development" section: installing the hook with `pre-commit install`, that it needs the virtual environment active, running all hooks with `pre-commit run --all-files`, and fixing findings with `ruff format` and `ruff check --fix`; also correct the sentence that says configuration stays at the repository root (it's in `config/`, and data in the data directory); verify the documented commands work as written

## 4. CI

- [x] 4.1 Add a `quality` job to `.github/workflows/ci.yml` that installs `requirements-dev.txt` on Python 3.14 and runs `pre-commit run --all-files`, and update the README's sentence about what GitHub Actions runs on each pull request; verify the workflow file loads with `yaml.safe_load` (PyYAML comes with `pre-commit`), and that the job's command exits 0 on the branch and non-zero, naming the file, when a file is temporarily unformatted (revert it afterwards)

## Workflow follow-up

- Open a pull request from `add-code-quality-checks`. The `test` and `quality` checks must pass, and `archive-check` is expected to fail until the archive. Confirm `quality` appears as its own check, separate from `test`.
- Once `quality` has run on the pull request, the repository owner adds it to the required checks for `main`.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and `test` and `quality` must pass again.
- Archive the change on this branch as the last step, which syncs the new code-quality spec and the continuous-integration spec, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
