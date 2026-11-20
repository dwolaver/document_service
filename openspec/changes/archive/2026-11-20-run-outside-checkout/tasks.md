# Tasks

## 1. Dependency

- [x] 1.1 Create a branch `run-outside-checkout` from `main`. Add `platformdirs` to `[project] dependencies` in `pyproject.toml` and `platformdirs==4.14.8` to `requirements.txt`, then run `pip install -r requirements-dev.txt`. Verify that `python -c "import platformdirs; print(platformdirs.__version__)"` prints 4.14.8, and that mypy finds its types with no `import-untyped` error

## 2. Packaged configuration

- [x] 2.1 `git mv config src/rfc_qa/config` and declare `[tool.setuptools.package-data] rfc_qa = ["config/*.json"]`. Verify that the root has no `config/` directory and `git status` shows the three files as renames
- [x] 2.2 In `paths.py`, make the selected configuration directory hold a `Traversable` and its source. The default is `importlib.resources.files("rfc_qa") / "config"`, with the source `packaged defaults`. A flag, variable or argument gives a `pathlib.Path`, with its precedence, relative-path and empty-variable rules unchanged, and a missing directory still raises `ConfigDirError`. Add tests that the default is inside the imported package and holds the three files, and that the existing precedence tests pass against it
- [x] 2.3 Make `load_query_config`, `load_corpus` and `load_config` accept `str | Traversable` and read with `.open(encoding="utf-8")`, with errors naming the file. Have `rfc-ingest` and `rfc-query` use the selected directory's files, and have `rfc-query` pass `None` to `query()` for the packaged defaults. Update the tests that read `DEFAULT_CONFIG_DIR` to use the packaged directory. Add tests that a selected directory missing `query.json` or `corpus.json` fails with a message naming that file, without using the packaged copy. Verify with `pytest tests/test_paths.py tests/test_query.py tests/ingestion/test_ingest.py`
- [x] 2.4 Change the `--config-dir` help in `rfc-ingest` and `rfc-query` to name `$RFC_QA_CONFIG_DIR`, then the packaged defaults. Update the README's configuration sections: the files are in `src/rfc_qa/config/`, they're edited in place in an editable install, and after a regular install they're copied into a directory for `--config-dir`, with the one-line command that prints where they are. Update the update-architecture skill's reading list to the new paths. Verify `--help` output for both commands, and that `grep -n "config/" README.md` only shows the new location or `--config-dir` examples

## 3. User data directory

- [x] 3.1 In `paths.py`, make the default data directory `platformdirs.user_data_dir("rfc-qa", appauthor=False)`, called when the directory is resolved, keeping the flag and variable precedence. Add an autouse fixture in `tests/conftest.py` that points the default at a temporary directory. Add tests that the real default is what `platformdirs` returns for `rfc-qa`, and that changing `XDG_DATA_HOME` changes it on Linux. Update the tests that expected `REPO_ROOT/data`. Verify with `pytest`, and that the real user data directory isn't created or changed by the run
- [x] 3.2 Change the `--data-dir` help in all three commands to name `$RFC_QA_DATA_DIR`, then the user data directory, with its resolved path. Update the README's data sections with the new default and a migration note for an existing checkout `data/` (move it there, or set `RFC_QA_DATA_DIR=data`), and add a line in Development saying the `OLLAMA_TESTS=1` test needs an index in the default data directory. Verify `--help` output for the three commands

## 4. No checkout references

- [x] 4.1 Remove `REPO_ROOT` and the "editable installs only" paragraph from `paths.py`, and update its docstring. Give the tests that need the repository root their own value, computed from the `tests` directory, in a shared helper. Update the README's Development section to say that a regular install also works, and drop the editable-only wording. Verify that `grep -rn "REPO_ROOT\|dirname" src/` finds no reference to the checkout, and that `pytest` passes

## 5. Install check

- [x] 5.1 Add `tests/test_install.py`, marked `install` (registered in `pytest.ini`), skipped unless `RFC_QA_INSTALL_TESTS=1`, following the design. Mention the variable in the README's Development section. Verify it passes with the variable set and is skipped without it
- [x] 5.2 Verify that the test catches the failures in the continuous-integration spec. With the `package-data` line removed, it fails because the configuration is missing. With the packaged default temporarily pointed at a checkout path, it fails. Restore both and confirm it passes
- [x] 5.3 Set `RFC_QA_INSTALL_TESTS: "1"` on the `test` job's test step in `.github/workflows/ci.yml`. Verify on the pull request that the `test` job runs the install test rather than skipping it

## 6. Verification

- [x] 6.1 Run `pytest` and `pre-commit run --all-files`, and verify that the only changes in test counts are the tests added and replaced here, and that ruff, the format check, mypy and gitleaks pass
- [x] 6.2 In a scratch venv, do a regular `pip install .` and run `rfc-query` from `/tmp` with `RFC_QA_DATA_DIR` set to the checkout's existing `data/`. Verify it answers a corpus question with sources, as the editable install does. Run `rfc-search` and `rfc-ingest --help` there too. Then check the remaining project-packaging scenarios against the editable install: module runs from another directory, the default data directory, and an edited packaged file being read

## Workflow follow-up

- Open a pull request from `run-outside-checkout`. It should say that the default data directory moved, and how to keep using an existing `data/`. The `test`, `quality` and `secrets` checks must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and the checks must pass again.
- Archive the change on this branch as the last step, which syncs the project-packaging and continuous-integration specs, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
