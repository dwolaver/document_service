# Tasks

## 1. Rules

- [x] 1.1 Create a branch `tighten-lint-rules` from `main`. Add `"E501", "SIM", "RUF", "PERF", "PT"` to `[tool.ruff.lint] select` in `pyproject.toml`, and extend its comment with a line for each group. Verify that `ruff check src scripts tests --statistics` reports exactly the 57 findings in the design's table: `E501` 1, `SIM115` 5, `SIM300` 1, `RUF043` 10, `RUF046` 2, `RUF012` 2, `RUF005` 1, `PERF401` 1, `PT006` 16, `PT018` 14, `PT007` 2, `PT019` 1 and `PT012` 1

## 2. Fixes

- [x] 2.1 Fix the ten `RUF043` patterns as in the design: raw strings, with a literal `.` escaped in `ARCHITECTURE\.md`, `module\.py` and `notes\.txt`. For each changed test, verify that it passes, and that it fails when the expected text in its pattern is changed by one character. Verify with `pytest tests/ingestion tests/scripts`
- [x] 2.2 Replace the five `open(...).read()` calls with `pathlib.Path(...).read_bytes()` or `.read_text()`, rewrite the `SIM300` assertion and the `RUF005` concatenation, and annotate the test fakes' shared class attributes as `ClassVar`. Verify with `pytest tests/generation tests/ingestion tests/retrieval tests/test_query.py` and `mypy tests`
- [x] 2.3 In the package and the script, drop the two redundant `int()` casts around `round()`, and make `_other_changes` return a list comprehension. Verify with `mypy src scripts` and `pytest tests/test_query.py tests/generation tests/scripts`
- [x] 2.4 Split the long `SYSTEM_PROMPT` line with a backslash continuation. Verify in a one-off script that the new `SYSTEM_PROMPT` equals `main`'s, character for character, and with `pytest tests/generation`
- [x] 2.5 Fix the `PT006` and `PT007` findings with `ruff check --fix --unsafe-fixes --select PT006,PT007 tests`, and review the diff. Split the 14 composite asserts by hand. Rename the `_isolated_default_data_dir` fixture to `isolated_default_data_dir`, and move the `try` out of the `pytest.raises` block in `test_one_kind_is_not_caught_by_another`. Before and after, run `pytest --collect-only -q`, and verify that it collects the same test IDs, so no parametrized case was lost or renamed. Verify with `pytest`

## 3. Checks

- [x] 3.1 Verify that `ruff check src scripts tests` passes with no findings, and that `grep -rn "noqa" src scripts tests` finds nothing. Temporarily add a 111-character comment to `src/rfc_qa/paths.py`, and to a test an `open(path).read()` and an `assert a and b`. Verify that `ruff check` reports `E501`, `SIM115` and `PT018`. Then remove all three
- [x] 3.2 Run `pytest`, with and without `RFC_QA_INSTALL_TESTS=1`, and `pre-commit run --all-files`. Verify that all pass
- [x] 3.3 From `/tmp`, run `rfc-search "Content-Length chunked"` and `rfc-search --index /nonexistent/index.db x`, and verify that stdout, stderr and the exit status match `main`

## Workflow follow-up

- Open a pull request from `tighten-lint-rules`, listing the new groups, how each finding was fixed, and the groups left out with the reasons. The `test`, `quality` and `secrets` checks must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and the checks must pass again.
- Archive the change on this branch as the last step, which syncs the code-quality spec, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
