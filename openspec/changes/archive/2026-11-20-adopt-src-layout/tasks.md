# Tasks

## 1. Move the package

- [x] 1.1 Create a branch `adopt-src-layout` from `main`, then `git mv rfc_qa src/rfc_qa`. Verify that `git status` shows only renames, that the root has no `rfc_qa/` directory (remove the leftover untracked `__pycache__` folders), and that `src/` contains only `rfc_qa/`
- [x] 1.2 In `pyproject.toml`, set `[tool.setuptools.packages.find]` to `where = ["src"]` with `include = ["rfc_qa*"]`, and the mypy settings to `mypy_path = "src"` and `files = ["src", "scripts", "tests"]`. Remove the old root `rfc_qa.egg-info/` and run `pip install -r requirements-dev.txt`. Verify that `python -c "import rfc_qa.paths as p; print(p.__file__)"` prints a path under `src/rfc_qa/`

## 2. Find the repository root

- [x] 2.1 In `src/rfc_qa/paths.py`, compute `REPO_ROOT` as the directory two levels above the package, and update the module docstring to say so. Add a test to `tests/test_paths.py` that `REPO_ROOT` contains `pyproject.toml` and `config/`. Verify the test fails before the `REPO_ROOT` fix and passes after it, and that `pytest tests/test_paths.py` passes

## 3. Documentation and comments

- [x] 3.1 Update the README's Development section to say the code is in the `rfc_qa` package in `src/`, that the commands and `python -m` need the project installed, and that an existing editable install must be reinstalled after this change. Update the strict mypy sentence to name `src/rfc_qa`. Verify with `grep -n "rfc_qa" README.md` that no line describes the package as being at the root
- [x] 3.2 Update the comment in `pytest.ini`, the root allow-list comment in `tests/test_packaging.py`, and the reading list in `.claude/skills/update-architecture/SKILL.md` to name `src/rfc_qa`. Verify with a grep, excluding the archive, `ARCHITECTURE.md` and the venv, that no file still refers to an `rfc_qa/` directory at the root

## 4. Verification

- [x] 4.1 Run `pytest` and `pre-commit run --all-files`, and verify that the test count is unchanged apart from the new test, and that ruff, the format check, mypy and gitleaks pass
- [x] 4.2 Check the spec scenarios against the real commands: `rfc-query --help`, `rfc-search --help` and `rfc-ingest --help` work, `python -m rfc_qa.ingestion.ingest --help` works from the repository root, and `python -m rfc_qa.query` with a question reads `config/` and `data/` at the repository root when run from another directory, as `rfc-query` does. Verify that a fresh venv without the project installed reports `No module named 'rfc_qa'` for `python -m rfc_qa.query` from the repository root
- [x] 4.3 In a scratch clone of the branch, create a fresh venv and run `pip install -r requirements-dev.txt` and `pytest`. Verify the tests pass, so that a new clone, as in CI, doesn't depend on files left over in this working copy

## Workflow follow-up

- Open a pull request from `adopt-src-layout`, saying that an existing editable install must be reinstalled after pulling. The `test`, `quality` and `secrets` checks must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and the checks must pass again.
- Archive the change on this branch as the last step, which syncs the project-packaging spec, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
