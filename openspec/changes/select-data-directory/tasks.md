# Tasks

## 1. Data directory resolution

- [x] 1.1 Add `RFC_QA_DATA_DIR` to the variables `tests/conftest.py` clears; verify the suite passes with `RFC_QA_DATA_DIR` exported to a junk value
- [x] 1.2 In `rfc_qa/paths.py`, rename `ConfigDir` to `SelectedDir`, move the shared precedence into a private helper, and add `DEFAULT_DATA_DIR`, `DATA_DIR_ENV`, `RFCS_FOLDER`, `INDEX_FILE` and `resolve_data_dir(explicit=None, explicit_source="--data-dir")`, as in design.md; keep `DATA_DIR` and `INDEX_PATH` until groups 2 to 4 stop using them; verify with `tests/test_paths.py`, updated for the rename and extended for the data directory: explicit over environment over default, an empty variable counts as unset, relative explicit and environment paths resolve from the working directory, and a missing directory is returned rather than raised; the existing configuration directory tests still pass

## 2. Ingestion

- [x] 2.1 In `rfc_qa/ingestion/ingest.py`, default `--data-dir` to `None` and resolve it with `paths.resolve_data_dir` in `main`; take `rfcs` and `index.db` from `paths.RFCS_FOLDER` and `paths.INDEX_FILE` in `run_ingestion`; remove `DEFAULT_DATA_DIR`; verify with tests in `tests/ingestion/test_ingest.py`: with no flag the data directory is `data/` at the repository root, `RFC_QA_DATA_DIR` selects another directory, `--data-dir` wins over the variable, and a data directory that doesn't exist is created (replace `run_ingestion` with a recorder for the selection tests, as the configuration directory tests do)
- [x] 2.2 Document `--data-dir`, `RFC_QA_DATA_DIR` and the precedence in the README's "Building the index" section, replacing the sentence that says the index is written to `data/` "unless `--data-dir` says otherwise"; verify `rfc-ingest --help` matches the README

## 3. Search

- [x] 3.1 In `rfc_qa/retrieval/keyword_index.py`, add `--data-dir`, default `--index` to `None`, use `--index` when it's given and otherwise `paths.INDEX_FILE` in `paths.resolve_data_dir(args.data_dir)`, and remove `DEFAULT_INDEX_PATH`; verify with tests in `tests/retrieval/test_keyword_index.py`: `--data-dir` and `RFC_QA_DATA_DIR` each find `index.db` in the directory they name, `--index` wins over `RFC_QA_DATA_DIR`, and a data directory without an index exits non-zero with the "Run rfc-ingest" message and doesn't create an index file
- [x] 3.2 Document `rfc-search --data-dir` and `--index` in the README beside the `rfc-search` examples; verify `rfc-search --help` matches the README

## 4. Query

- [x] 4.1 Remove `index_path` from `config/query.json` and `QueryConfig`; pass the index path to `_answer` as an argument, with no check for a leftover `index_path` key; verify with tests in `tests/test_query.py`: the real configuration loads (removing the relative, absolute and working-directory `index_path` tests and the two `index_path` cases in the invalid-value table)
- [x] 4.2 Add `query(user_query, *, config_dir=None, data_dir=None)`, resolving the data directory with `explicit_source="data_dir argument"`; add `--data-dir` to `main`, resolving it there beside `--config-dir` and passing both paths to `query`; change the `setup` fixture to build `index.db` in a temporary data directory selected with `RFC_QA_DATA_DIR`, and move every `_with(index_path=...)` test to selecting a data directory; verify with tests: `data_dir` wins over `RFC_QA_DATA_DIR`, which wins over the default, `main --data-dir` selects the index, a data directory without an index gives `INDEX_UNAVAILABLE` naming the index path and `rfc-ingest`, and the existing pipeline, timing and console tests pass unchanged apart from how they select the index
- [x] 4.3 Remove `DATA_DIR` and `INDEX_PATH` from `rfc_qa/paths.py`; verify `grep -rn "DATA_DIR\b\|INDEX_PATH\|index_path" rfc_qa config` finds no `index_path` configuration key or old constant, only the index path passed between functions, and the full suite passes
- [x] 4.4 Update the README's "Asking a question" section: remove the sentence about a relative `index_path`, and document `--data-dir`, `RFC_QA_DATA_DIR`, and the `data_dir` argument; verify `rfc-query --help` matches the README and the README no longer describes `index_path` as a setting

## 5. Integration check

- [x] 5.1 From a directory outside the checkout, run `rfc-search` and `rfc-query` with no overrides and check they read `data/index.db` at the repository root; then run `rfc-ingest` with `--data-dir` pointing to a scratch directory seeded with a copy of `data/rfcs`, and check `rfc-search` and `rfc-query` find that index with `--data-dir` and then with `RFC_QA_DATA_DIR`, by changing `target_chunk_tokens` in a copied configuration directory and checking the chunk IDs or count differ from the default index; run `rfc-query` and `rfc-search` with `--data-dir` naming an empty directory and check both report the missing index and `rfc-ingest`; verify each behaves as the specs say
- [x] 5.2 Run `pytest` with `RFC_QA_CONFIG_DIR`, `RFC_QA_DATA_DIR` and `OLLAMA_BASE_URL` exported to junk values, and again without them; verify both give the same pass and skip counts

## Workflow follow-up

- Open a pull request from `select-data-directory`. The `test` check must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and `test` must pass again.
- Archive the change on this branch as the last step, which syncs the project-packaging and answer-generation specs, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
