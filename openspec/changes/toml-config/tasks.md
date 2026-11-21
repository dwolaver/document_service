# Tasks

## 1. Reader and files

- [x] 1.1 Create a branch `toml-config` from `main`. Add `paths.read_toml(file: ConfigFile) -> dict[str, Any]`, as in the design, and test that it reads a path and a packaged `Traversable`. Test that a missing file and a malformed file each raise `ConfigError` naming the file, with the cause chained, and that a malformed file's message gives the line and column. Test that a JSON document is rejected the same way. Verify with `pytest tests/test_paths.py`
- [x] 1.2 Move the three files with `git mv` to `corpus.toml`, `ingest.toml` and `query.toml`, and rewrite each in TOML with the header, section and setting comments from the design, checking each comment against the code. Keep the corpus order and group it under `# HTTP`, `# TLS` and `# TCP`. Before deleting the JSON copies, verify in a one-off script that `tomllib.load` of each new file equals `json.load` of the file it replaces, taken from `main`
- [x] 1.3 Change `CORPUS_FILE`, `INGEST_CONFIG_FILE` and `QUERY_CONFIG_FILE` in `paths.py` to the `.toml` names, and `package-data` in `pyproject.toml` to `config/*.toml`. Verify that `grep -rn '\.json' src/rfc_qa pyproject.toml` finds only the Ollama request code, and no configuration file name

## 2. Loaders

- [x] 2.1 Make `ingest.load_corpus` and `ingest.load_config` read through `paths.read_toml`, and remove `_load_json`, its `json` import and the "must be a JSON object" check. Verify that the messages of every other validation rule are unchanged, with `pytest tests/ingestion/test_ingest.py` after 3.1
- [x] 2.2 Make `query.load_query_config` read through `paths.read_toml`, and remove its inline `json.load` and the "must be a JSON object" check. Keep the `OLLAMA_BASE_URL` override. Verify with `pytest tests/test_query.py` after 3.1

## 3. Tests

- [x] 3.1 Add `write_toml(path, data) -> str` to `tests/conftest.py`, as in the design, with a test that it round-trips through `tomllib` for the shapes the tests use, leaving out `None` values. Convert `_write_json` in `tests/ingestion/test_ingest.py` and `_write_config` in `tests/test_query.py` to it, rename their files to `.toml`, and change the packaged-file names in those tests. Replace the invalid-JSON test with an invalid-TOML test that checks the file, line and column in the message, and drop the top-level-list case. Add a test that `rfc-ingest --corpus` naming a JSON file exits 1 with a configuration error naming it, before downloading. Verify with `pytest tests/ingestion/test_ingest.py tests/test_query.py`
- [x] 3.2 In `tests/test_packaging.py`, add the comment test from the design for the three packaged files, and extend the repository-root check to the `.toml` names as well as the old JSON names. Verify that it passes, and that it fails when a temporary setting without a comment is added to `query.toml`. Then remove it
- [x] 3.3 In `tests/test_install.py`, change `CONFIG_FILES` to the `.toml` names, and read the packaged corpus with `tomllib` in `_seed_corpus`. Verify with `RFC_QA_INSTALL_TESTS=1 pytest tests/test_install.py`, which checks that the wheel holds the TOML files and no JSON

## 4. Documentation and checks

- [x] 4.1 Update the README:
  - the file names and links;
  - the `--corpus small-corpus.toml` example;
  - the configuration-directory text, saying the files are TOML and each setting is described in its file;
  - no mention of the earlier JSON format, as the repository owner asked in review.

  Verify that `grep -in 'json' README.md` finds nothing
- [x] 4.2 Run `pytest`, with and without `RFC_QA_INSTALL_TESTS=1`, and `pre-commit run --all-files`. Verify that all pass, and that `grep -rn 'corpus\.json\|ingest\.json\|query\.json\|_load_json\|JSON object' src tests` finds nothing
- [x] 4.3 From `/tmp`, run `rfc-ingest` with `--data-dir` on a scratch copy of the data directory, and `rfc-query` and `rfc-search` against the real index. Verify that each gives the same stdout as on `main`, so the chunk count, the matches and the answer's sources are unchanged. Copy the packaged config into a scratch directory with the README's `cp` command, break one line in its `query.toml`, and verify that `rfc-query --config-dir` on it exits 1 with one stderr line naming the file, the line and the column

## Workflow follow-up

- Open a pull request from `toml-config`, marking the move from JSON to TOML as breaking. The `test`, `quality` and `secrets` checks must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and the checks must pass again.
- Archive the change on this branch as the last step, which syncs the project-packaging and rfc-ingestion specs, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
