# Proposal

## Why

Each module reports failures its own way:

- `download_rfc` prints to stderr and returns `False`, as the rfc-downloader spec requires.
- `search` and `read_metadata` print, then return `None`. `build_index` prints, then returns `False`.
- `query.py`, `ingest.py` and `answer_generator.py` raise five unrelated exception classes, and one
  of them, `ConfigDirError`, is a `ValueError`.

So a caller can't catch "anything this library reports" in one place, and the library writes to the
terminal of a program that embeds it. Messages also get shown twice: when the index is missing,
`rfc-query` prints `Index not found ...` from `read_metadata`, then the query's own error. A bad RFC
number is reported the same way as a network failure, though one is a bug in the caller and the
other isn't.

## What Changes

- A new `rfc_qa.errors` module defines `RfcQaError`, and under it one subclass per kind of failure:
  - `ConfigError`, which replaces `ConfigDirError` and `QueryConfigError`. It also covers an invalid
    corpus manifest or ingestion configuration, which `IngestError` reports today.
  - `DownloadError`, `IngestError`, `IndexUnavailableError` and `IndexBuildError`.
  - `ModelUnavailableError` and `ModelResponseError`, which move here.

  Each one's message is ready to show as it is.
- Library code never prints. A failure the user or the environment causes raises one of those
  classes. When it was caused by another exception, that exception is chained as its cause. **BREAKING**
  for code that relied on the return values below.
- A caller bug raises the built-in `TypeError` or `ValueError`. **BREAKING**:
  - `download_rfc` with a non-integer or `bool` number raises `TypeError`, and with a number below 1
    raises `ValueError`. It used to return `False`.
  - `query()` with a non-string raises `TypeError`. It used to return `INVALID_QUERY`. An empty or
    whitespace-only string is user input, so it still returns `INVALID_QUERY`.
- `download_rfc` returns the path of `rfc<number>.txt`, whether it was downloaded now or was
  already there, and raises `DownloadError` on any other failure. **BREAKING**: it used to return
  `True` or `False`.
- `search` and `read_metadata` raise `IndexUnavailableError` when the index is missing or can't be
  read. `build_index` raises `IndexBuildError` and returns nothing. **BREAKING**: they used to return
  `None` or `False`.
- `query()` keeps returning a `QueryResponse` for every expected failure. It maps each error class to
  the same code as today, and `QueryResponse` and `QueryErrorCode` don't change.
- `rfc-ingest`, `rfc-search` and `rfc-query` catch `RfcQaError`, print its message once to stderr,
  and exit 1. They don't catch other exceptions, so a bug shows its traceback. Argument errors from
  `argparse` keep their usage message and exit status 2.

## Capabilities

### New Capabilities

- `error-handling`: how the library reports failures (one base class, ready-to-show messages, no
  printing), how caller bugs are reported, and how the commands turn errors into one line on stderr
  and an exit status.

### Modified Capabilities

- `rfc-downloader`: returns the file path, raises instead of returning `False`, never prints, and
  treats an invalid number as a caller bug.
- `rfc-ingestion`: searching or reading a missing index raises, building an index raises on failure,
  and the commands report errors once.
- `query-interface`: a non-string query raises `TypeError`, and the console prints a failure once.

## Impact

- Code:
  - New `src/rfc_qa/errors.py`.
  - `ingestion/rfc_downloader.py`, `retrieval/keyword_index.py`, `ingestion/ingest.py`, `query.py`,
    `paths.py` and `generation/answer_generator.py` raise the new classes and drop their `_log_error`
    helpers.
  - The three `main()` functions share one way of reporting errors.
- API: the return values of `download_rfc`, `build_index`, `search` and `read_metadata`, the classes
  callers catch, and `query()` with a non-string. The project isn't deployed, so nothing outside the
  repository depends on these.
- Tests: those that checked return values or captured stderr from library functions check the raised
  error instead. New tests check that no library function prints and that each command reports an
  error once.
- `scripts/update_architecture.py` is a release script, not library code, and keeps its own
  `ArchitectureError`.
- README: a short section on the errors a Python caller can catch.
