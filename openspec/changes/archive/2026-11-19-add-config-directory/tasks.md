# Tasks

## 1. Configuration directory resolution

- [x] 1.1 Add `tests/conftest.py` with an autouse fixture that removes `RFC_QA_CONFIG_DIR` and `OLLAMA_BASE_URL` from the environment; verify the suite still passes with both variables exported to junk values in the shell
- [x] 1.2 Add `DEFAULT_CONFIG_DIR`, `CONFIG_DIR_ENV`, the three file-name constants, `ConfigDir`, `ConfigDirError` and `resolve_config_dir(explicit=None, explicit_source="--config-dir")` to `rfc_qa/paths.py`, as in design.md; verify with a new `tests/test_paths.py` that covers: explicit over environment over default, an empty variable counts as unset, relative explicit and environment paths resolve from the working directory (`monkeypatch.chdir`), and a missing directory raises with the path and the source in the message

## 2. Move the configuration files

- [x] 2.1 Run `git mv corpus.json config/corpus.json`, `git mv ingest_config.json config/ingest.json` and `git mv query_config.json config/query.json`, and set the file-name constants in `paths.py` to those names; remove `CORPUS_PATH`, `INGEST_CONFIG_PATH` and `QUERY_CONFIG_PATH` from `paths.py`; and point the tests that load the real files (`test_real_config_loads`, `test_default_config_is_at_the_repository_root`, and the real corpus and config tests in `tests/ingestion/test_ingest.py`) at `paths.DEFAULT_CONFIG_DIR`; verify `git status` shows all three moves as renames, and the full suite passes once groups 3 and 4 no longer import the removed constants (do 2.1 together with 3.1 and 4.1 if needed to keep the suite green)
- [x] 2.2 Update the README's references to the three files, links and text alike (for example "`query_config.json` sets the model"), to the new paths and names; verify each link resolves to an existing file and the README no longer names `ingest_config.json` or `query_config.json`

## 3. Ingestion

- [x] 3.1 In `rfc_qa/ingestion/ingest.py`, add `--config-dir`, default `--corpus` and `--config` to `None`, and in `main` resolve the configuration directory only when one of those files is missing, reporting `ConfigDirError` on stderr with exit code 1 before any download; remove `DEFAULT_CORPUS_PATH` and `DEFAULT_CONFIG_PATH`; verify with tests in `tests/ingestion/test_ingest.py`: defaults read from `config/`, `RFC_QA_CONFIG_DIR` and `--config-dir` select another directory, `--corpus` with `--config-dir` takes the corpus from the file and the configuration from the directory, a missing directory exits 1 naming the directory and its source without calling `download_rfc`, and a missing directory is ignored when both file flags are given
- [x] 3.2 Document `--config-dir`, `RFC_QA_CONFIG_DIR` and the precedence in the README's "Building the index" section; verify `rfc-ingest --help` matches the README

## 4. Query

- [x] 4.1 In `rfc_qa/query.py`, add `query(user_query, *, config_dir=None)`, resolve the directory with `explicit_source="config_dir argument"`, turn `ConfigDirError` into a `CONFIG_INVALID` failure, add `--config-dir` to `main` (resolved in `main` with the label `--config-dir`, printing errors to stderr with exit 1), and remove `CONFIG_PATH`; verify with tests in `tests/test_query.py`, which now select configuration through `config_dir` or the environment instead of monkeypatching `CONFIG_PATH`, writing their temporary configuration as `query.json` (and `ingest.json` in the ingestion tests) so the directory lookup finds it: precedence, a missing directory gives `CONFIG_INVALID` naming the directory and source, and `main` with a missing `--config-dir` exits 1 naming `--config-dir`
- [x] 4.2 Add a test that a query configuration in a directory outside the repository, with a relative `index_path`, resolves the index from the repository root; verify it passes
- [x] 4.3 Document `--config-dir`, `RFC_QA_CONFIG_DIR` and the `config_dir` argument in the README's "Asking a question" section; verify `rfc-query --help` matches the README

## 5. Ollama address override

- [x] 5.1 In `load_query_config`, replace the validated `llm.base_url` with `OLLAMA_BASE_URL` when it's set and not empty; verify with tests: the variable set gives that `base_url`, unset or empty gives the configured one, and a missing `llm.base_url` in the file is still a `CONFIG_INVALID` error even with the variable set
- [x] 5.2 Document `OLLAMA_BASE_URL` in the README beside the query configuration; verify the documented behavior matches the 5.1 tests

## 6. Skill and integration check

- [x] 6.1 Update step 3 of `.claude/skills/update-architecture/SKILL.md` to read `config/corpus.json`, `config/ingest.json` and `config/query.json`; verify no other line in the skill names the old paths or file names
- [x] 6.2 From a directory outside the checkout: run `rfc-search` and `rfc-query` with no overrides; copy `config/` to the scratch directory, change `retrieval.limit` there, and run `rfc-query` with `RFC_QA_CONFIG_DIR` and then with `--config-dir`, checking the source count follows the copy; run `rfc-query` with a missing `--config-dir`; and run `rfc-query` with `OLLAMA_BASE_URL=http://127.0.0.1:11434` (answers) and `OLLAMA_BASE_URL=http://127.0.0.1:1` (model unavailable, naming that address); verify each behaves as the specs say
- [x] 6.3 Run `rfc-ingest` with `RFC_QA_CONFIG_DIR` pointing to the scratch copy and `--data-dir` in the scratch directory, then with `RFC_QA_CONFIG_DIR` pointing to a missing directory; verify the first builds an index from the copied configuration and the second exits 1 before downloading
- [x] 6.4 Run `pytest` with `RFC_QA_CONFIG_DIR` and `OLLAMA_BASE_URL` exported to junk values, and again without them; verify both give the same pass and skip counts, and that the repository root has no `.json` configuration files left

## Workflow follow-up

- Open a pull request from `add-config-directory`. The `test` check must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and `test` must pass again.
- Archive the change on this branch as the last step, which syncs the project-packaging and answer-generation specs, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
