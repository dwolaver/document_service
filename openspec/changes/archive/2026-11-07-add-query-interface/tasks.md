# Tasks

## 1. Response type and error codes

- [x] 1.1 Define the `QueryResponse` dataclass (`success`, `answer`, `error_string`, `error_code`, with defaults) and a `QueryErrorCode` `IntEnum` (`INVALID_QUERY`, `NOT_IMPLEMENTED`) in `query.py`; verify a unit test constructs a response and reads its fields
- [x] 1.2 Add a stderr error-print helper consistent with `rfc_downloader._log_error`; verify it is used by the CLI failure path (covered by CLI tests in group 3)

## 2. Query API with validation and stub

- [x] 2.1 Implement `query(user_query)` input validation: reject non-`str`, empty, and whitespace-only queries with `QueryResponse(success=False, error_code=QueryErrorCode.INVALID_QUERY)` and an `error_string`; verify unit tests cover `None`, a non-string (e.g. `123`), `""`, and `"   "`
- [x] 2.2 Implement the stub answer path: a valid query returns `QueryResponse(success=False, error_code=QueryErrorCode.NOT_IMPLEMENTED)` with a RAG-in-progress `error_string` and no answer; verify a unit test asserts `success is False`, the error code, and `answer is None`

## 3. Console entry point

- [x] 3.1 Implement `main(argv=None) -> int` using argparse with one positional query argument, calling `query()`; on success print `answer` to stdout and return `0`, on failure print `error_string` to stderr and return a non-zero code; add `if __name__ == "__main__": sys.exit(main())`; verify unit tests using `capsys` assert stdout/stderr routing and the return code for a failure (current stub) path
- [x] 3.2 Verify a unit test that `main` returns non-zero and writes the error string to stderr for an invalid-query argument, and (via monkeypatching `query` to return a success response) that a successful response prints the answer to stdout and returns `0`

## 4. Suite verification

- [x] 4.1 Run the full `pytest` suite and verify all query-interface and existing tests pass
