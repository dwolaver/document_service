# Tasks

## 1. Baseline and import mode

- [x] 1.1 Save the collected test IDs before any move (`pytest --collect-only -q`, 323 tests) to the scratch directory, with the folders removed from each file path (but not from slashes inside parametrized IDs, such as `HTTP/2`), so they compare across paths; verify the file lists 323 IDs, each starting with a test file name
- [x] 1.2 Add `addopts = --import-mode=importlib` to `pytest.ini`, keeping `pythonpath = .` and its comment, and extend the comment to say why the import mode is set; verify `pytest` still gives 321 passed, 2 skipped

## 2. Move the tests

- [x] 2.1 `git mv` `test_rfc_downloader.py`, `test_rfc_parser.py`, `test_chunker.py`, `test_ingest.py` and `fixtures/` into `tests/ingestion/`, and replace `ROOT` in `test_ingest.py` with `rfc_qa.paths.REPO_ROOT`; verify `pytest tests/ingestion` passes with the same count those four files had before
- [x] 2.2 `git mv tests/test_keyword_index.py tests/retrieval/` and `git mv tests/test_answer_generator.py tests/generation/`; verify `pytest tests/retrieval tests/generation` passes
- [x] 2.3 `git mv tests/test_update_architecture.py tests/scripts/`; verify `pytest tests/scripts` passes, which shows that `tests/scripts/` doesn't shadow the real `scripts` package
- [x] 2.4 Update the fixtures path in the README's license section to `tests/ingestion/fixtures/`; verify the README has no other `tests/` paths that point to old locations

## 3. Integration check

- [x] 3.1 Remove `tests/__pycache__`, then run `pytest` from the repository root; verify 321 passed, 2 skipped, and that the collected test IDs, with paths stripped as in 1.1, are identical to the baseline
- [x] 3.2 Verify `tests/` matches the layout in design.md (only `test_query.py` and `test_packaging.py` at the top level), that `git status` shows every move as a rename, and that only `test_ingest.py` has content changes among the tests

## Workflow follow-up

- Open a pull request from `organize-tests-by-package`. The `test` check must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and `test` must pass again.
- Archive the change on this branch as the last step, which makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
