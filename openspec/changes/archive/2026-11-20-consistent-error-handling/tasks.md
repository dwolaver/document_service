# Tasks

## 1. Error classes and reporting

- [x] 1.1 Create a branch `consistent-error-handling` from `main`. Add `src/rfc_qa/errors.py` with `RfcQaError` and its seven subclasses, as in the design. Add `tests/test_errors.py` with tests that each subclass is an `RfcQaError`, that none is a `TypeError` or `ValueError`, and that `str()` of each is the message it was given. Verify with `pytest tests/test_errors.py` and mypy
- [x] 1.2 Add `src/rfc_qa/cli.py` with `report_error(message: object) -> int`, which prints the message as one line to stderr and returns 1. Test that it writes exactly that line to stderr, nothing to stdout, and returns 1

## 2. Configuration errors

- [x] 2.1 Make `resolve_config_dir`, `load_query_config`, `load_corpus` and `load_config` raise `ConfigError`, chaining the `OSError` or JSON error where there is one, and remove `ConfigDirError` and `QueryConfigError`. Update the tests that expected the old classes, and the test that `ConfigDirError` is a `ValueError`. Add a test that an invalid manifest raises `ConfigError` before anything is downloaded. Verify with `pytest tests/test_paths.py tests/test_query.py tests/ingestion/test_ingest.py`

## 3. Downloader

- [x] 3.1 Make `download_rfc` return the path of `rfc<number>.txt`, raise `TypeError` for a non-`int` or `bool` number and `ValueError` for one below 1, and raise `DownloadError` for every other failure, naming the RFC and chaining the cause. Remove its `_log_error`, and keep the temporary-file cleanup. Update `tests/ingestion/test_rfc_downloader.py`: each failure scenario checks the raised class, the message, that no file and no temporary file remain, and that nothing was printed. Test that a request error is the `__cause__`, and that an existing file returns its path without a request. Verify with `pytest tests/ingestion/test_rfc_downloader.py`

## 4. Index

- [x] 4.1 Make `build_index` raise `IndexBuildError` and return `None`, and make `read_metadata` and `search` raise `IndexUnavailableError` for a missing file or a `sqlite3.Error`, with messages naming the path and `rfc-ingest`. Remove its `_log_error`. Update `tests/retrieval/test_keyword_index.py` for the missing-index, unreadable-index and failed-build scenarios, each checking that nothing was printed, the existing index is unchanged, and no temporary file or new index file remains. Verify with `pytest tests/retrieval/test_keyword_index.py`

## 5. Ingestion

- [x] 5.1 In `run_ingestion`, let `DownloadError` and `IndexBuildError` propagate, raise `IngestError` for an RFC with no chunks and for an `OSError` reading a stored RFC (chained), and drop the `False` checks. Make `rfc-ingest` catch `RfcQaError` and return `report_error(exc)`, and remove its `_log_error`. Add tests that a failed download and an unreadable RFC each exit 1 with one stderr line naming the RFC, and that no index is written. Verify with `pytest tests/ingestion/test_ingest.py`

## 6. Query and search

- [x] 6.1 Move `ModelUnavailableError` and `ModelResponseError` to `errors.py`, and update `answer_generator` and its tests to import them from there. Verify with `pytest tests/generation`
- [x] 6.2 In `query()`, raise `TypeError` for a non-`str` query before reading anything, and map `ConfigError`, `IndexUnavailableError`, `ModelUnavailableError` and `ModelResponseError` to the existing codes with `str(exc)`. Report index metadata without a usable `target_chunk_tokens` as `IndexUnavailableError`. Update the non-string tests to expect `TypeError`. Add tests that each failure gives the same code as before, and that a failure response leaves stdout and stderr empty. Verify with `pytest tests/test_query.py`
- [x] 6.3 Make `rfc-query` and `rfc-search` report errors through `report_error`, catching `RfcQaError` around their work, and remove `query.py`'s `_log_error`. Add tests that `rfc-query` with no index prints exactly one stderr line, naming the index path and `rfc-ingest`, that `rfc-search` with a missing index does the same and exits 1, and that an unknown option still exits 2. Verify with `pytest tests/test_query.py tests/retrieval/test_keyword_index.py`

## 7. Never print, and documentation

- [x] 7.1 Add the `ast` test to `tests/test_errors.py`. It fails on `print`, `sys.stdout` or `sys.stderr` in `src/rfc_qa` outside `cli.py`, the `main` functions and the named output helpers. Verify it passes, and that it fails when a `print` is temporarily added to `keyword_index.search`
- [x] 7.2 Add a README section on errors for Python callers: catch `RfcQaError` from `rfc_qa.errors` or one of its subclasses, caller bugs raise `TypeError` or `ValueError`, `query()` returns a response for expected failures and raises `TypeError` for a non-string, and the commands print one line and exit 1. Verify the example in it runs as written

## 8. Verification

- [x] 8.1 Run `pytest`, with and without `RFC_QA_INSTALL_TESTS=1`, and `pre-commit run --all-files`. Verify that all pass, and that `grep -rn "_log_error\|ConfigDirError\|QueryConfigError" src tests` finds nothing
- [x] 8.2 Check the error-handling scenarios with the real commands, from `/tmp`. Each of these should print exactly one stderr line and exit 1: `rfc-search --index /nonexistent/index.db x`, `rfc-query --data-dir /nonexistent x`, `rfc-ingest --config-dir /nonexistent` and `rfc-ingest --corpus` pointing at an invalid manifest. `rfc-search --bogus` should exit 2 with usage. Then check that a working query and search still give the same output as on `main`

## Workflow follow-up

- Open a pull request from `consistent-error-handling`, listing the changed return values and the `query()` `TypeError` as breaking. The `test`, `quality` and `secrets` checks must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and the checks must pass again.
- Archive the change on this branch as the last step, which creates the error-handling spec, syncs the rfc-downloader, rfc-ingestion and query-interface specs, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
