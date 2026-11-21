# Tasks

## 1. Logging foundation

- [x] 1.1 Create a branch `add-library-logging` from `main`. Before changing any code, save from `main` into the scratchpad the stdout, stderr and exit status of: `--help` for the three commands, `rfc-search --index /nonexistent/index.db x`, `rfc-query --data-dir /nonexistent x`, `rfc-ingest --config-dir /nonexistent`, and a working `rfc-search "Content-Length chunked"`. Verify each saved file is non-empty
- [x] 1.2 Add `LOG` and `G` to `[tool.ruff.lint] select` in `pyproject.toml`, extending the comment. Verify that `ruff check src scripts tests` still passes, and that a temporary `logger.info(f"x {x}")` in `src/rfc_qa/paths.py` is reported as `G004`. Then remove it
- [x] 1.3 Add the `NullHandler` on the `rfc_qa` logger in `src/rfc_qa/__init__.py`. Add a `conftest.py` fixture that restores the `rfc_qa` logger's level, handlers and `propagate` after each test. Add a test that the `rfc_qa` logger has a `NullHandler` and no other handler after `import rfc_qa`, and that a `WARNING` logged on `rfc_qa.paths` with no configuration writes nothing to stderr. Verify with `pytest tests/test_logging.py`

## 2. Library records

- [x] 2.1 Add a module logger to `paths.py`, and log the selected configuration and data directories with their source at `DEBUG`. Test with `caplog` that `resolve_config_dir` and `resolve_data_dir` each emit one `DEBUG` record from `rfc_qa.paths`, naming the directory and its source, for the flag, environment and default cases. Verify with `pytest tests/test_paths.py`
- [x] 2.2 Add a module logger to `rfc_downloader.py`. Log `INFO` before a request, naming the RFC and URL, and `DEBUG` for a file that's already stored and for the bytes stored. Test the records for a download and a skipped download, and that a failed download emits no record containing the error's message. Verify with `pytest tests/ingestion/test_rfc_downloader.py`
- [x] 2.3 Add a module logger to `ingest.py`. Log the manifest's RFC count and the total chunks at `INFO`, and each RFC's section and chunk counts at `DEBUG`. Test the records of an ingestion run with the fixture corpus. Verify with `pytest tests/ingestion/test_ingest.py`
- [x] 2.4 Add a module logger to `keyword_index.py`. Log `INFO` when writing the index, with the chunk count and path, and `DEBUG` for each search, with its query, limit and result count. Test the records, and that a missing index emits no record containing the error's message. Verify with `pytest tests/retrieval/test_keyword_index.py`
- [x] 2.5 Add module loggers to `query.py` and `answer_generator.py`, with the records in the design's table. Test an answered query and a not-found query for their `INFO` records. Test that the `DEBUG` records give the configuration file, the index path and the model's token counts, and that no record contains the prompt sent to the model. Verify with `pytest tests/test_query.py tests/generation`

## 3. Commands

- [x] 3.1 Add `add_verbose_argument` and `configure_logging` to `cli.py`, as in the design. Test that verbosity 0 adds no handler, 1 sets `INFO` and 2 sets `DEBUG` on the `rfc_qa` logger, that a second call replaces the handler instead of adding one, that the root logger is unchanged, and that a record is written to stderr as `LEVEL logger: message`. Verify with `pytest tests/test_errors.py tests/test_logging.py`
- [x] 3.2 Use both helpers in the `main()` of `rfc-ingest`, `rfc-search` and `rfc-query`. For each command, test that without `-v` stderr is empty on success, that `-v` writes `INFO` lines and no `DEBUG` lines to stderr while stdout matches the run without `-v`, and that `-vv` adds `DEBUG` lines. Test that with `-v` a failure ends stderr with the error's message, which appears once. Verify with `pytest tests/test_query.py tests/retrieval tests/ingestion/test_ingest.py`

## 4. Documentation and checks

- [x] 4.1 Add a README section on `-v`/`-vv`, with an example of `rfc-ingest -v` output, and on how a Python caller shows the records, with `logging.basicConfig(level=logging.INFO)` or a handler on the `rfc_qa` logger. Verify that the Python example runs as written and shows the records it describes
- [x] 4.2 Run `pytest`, with and without `RFC_QA_INSTALL_TESTS=1`, and `pre-commit run --all-files`. Verify that all pass, and that the never-prints test in `tests/test_errors.py` is unchanged
- [x] 4.3 From `/tmp`, run the commands from 1.1 without `-v`, and verify that stdout, stderr and the exit status match `main`, except for the new `-v` line in each `--help`. Then run `rfc-search -vv "Content-Length chunked"` and `rfc-query -v "What does a 404 status code mean?"` against the real index. Verify that stdout matches the run without `-v`, and that stderr holds only `rfc_qa` records in the `LEVEL logger: message` format

## Workflow follow-up

- Open a pull request from `add-library-logging`. Note that output without `-v` doesn't change, and that the library stays silent unless logging is configured. The `test`, `quality` and `secrets` checks must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and the checks must pass again.
- Archive the change on this branch as the last step, which creates the diagnostic-logging spec, syncs the error-handling, query-interface and code-quality specs, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
