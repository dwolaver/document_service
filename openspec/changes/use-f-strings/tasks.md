# Tasks

## 1. Baseline and lint rule

- [x] 1.1 Create a branch `use-f-strings` from `main`. Before changing any code, save the `--help` output of `rfc-ingest`, `rfc-search` and `rfc-query`, and the output and exit status of the error scenarios in 4.2, from `main` into the scratchpad. Verify each saved file is non-empty
- [x] 1.2 Add `"UP"` to `[tool.ruff.lint] select` in `pyproject.toml`, and add a comment on why it's there. Verify that `ruff check src scripts tests` now fails, and that every finding is `UP032`

## 2. Convert the calls

- [x] 2.1 Run `ruff check --select UP032 --fix src scripts tests`, then `ruff format`. Review the diff against the design's rules: an `f` prefix only on pieces with a placeholder, every `!r` and format spec kept, and a local variable where an inline expression would hide the wording. Verify with `pytest` and `ruff check`
- [x] 2.2 Convert the five calls that `UP032` leaves alone by hand: `scripts/update_architecture.py` lines 138, 238 and 245, `tests/test_query.py` line 377 and `tests/ingestion/test_ingest.py` line 336 (line numbers as on `main`). Verify with `pytest tests/scripts tests/test_query.py tests/ingestion/test_ingest.py`
- [x] 2.3 Replace `RFC_URL_TEMPLATE` with `_rfc_url(number: int) -> str`, and the test's `SKILL` constant with a function of the model name that returns the same text. Verify with `pytest tests/ingestion/test_rfc_downloader.py tests/scripts`, and that `grep -rn "RFC_URL_TEMPLATE" src tests scripts` finds nothing

## 3. Checks

- [x] 3.1 Verify that `grep -rn "\.format(" src scripts tests` finds nothing, and that `ruff check` passes with `UP` selected. Temporarily add `"x {}".format(1)` to `src/rfc_qa/paths.py`, and verify that `ruff check` reports it as `UP032` and fails. Then remove it
- [x] 3.2 Run `pytest`, with and without `RFC_QA_INSTALL_TESTS=1`, and `pre-commit run --all-files`. Verify that all pass

## 4. Output unchanged

- [x] 4.1 From `/tmp`, run `--help` for `rfc-ingest`, `rfc-search` and `rfc-query`, and verify each is identical to the copy saved from `main` in 1.1
- [x] 4.2 From `/tmp`, run each of these and verify its stdout, stderr and exit status match `main`: `rfc-search --index /nonexistent/index.db x`, `rfc-query --data-dir /nonexistent x`, `rfc-ingest --config-dir /nonexistent`, `rfc-ingest --corpus` with a duplicate-RFC manifest, and a working `rfc-search "Content-Length chunked"` against the real index

## Workflow follow-up

- Open a pull request from `use-f-strings`. Note that `RFC_URL_TEMPLATE` is removed, and that messages and command output don't change. The `test`, `quality` and `secrets` checks must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and the checks must pass again.
- Archive the change on this branch as the last step, which syncs the code-quality spec, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
