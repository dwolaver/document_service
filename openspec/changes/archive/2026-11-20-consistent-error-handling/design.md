# Design

## Context

How each module reports a failure today:

| Module | Expected failure | Caller bug |
| --- | --- | --- |
| `paths.py` | raises `ConfigDirError(ValueError)` | none checked |
| `query.py` | `load_query_config` raises `QueryConfigError(Exception)`. `query()` returns a response | non-string query returns `INVALID_QUERY` |
| `ingestion/ingest.py` | raises `IngestError(Exception)`, including for an invalid manifest or configuration | none checked |
| `ingestion/rfc_downloader.py` | prints, then returns `False` | prints, then returns `False` |
| `retrieval/keyword_index.py` | `search` and `read_metadata` print, then return `None`. `build_index` prints, then returns `False` | none checked |
| `generation/answer_generator.py` | raises `ModelUnavailableError(Exception)` and `ModelResponseError(Exception)` | none checked |

`ingest.run_ingestion` turns a `False` from `download_rfc` or `build_index` into an `IngestError`.
`query._answer` turns a `None` from `read_metadata` or `search` into an `INDEX_UNAVAILABLE` response.
So the same failure is described twice: once on stderr by the function that failed, and again by its
caller. An `OSError` while reading a stored RFC file isn't caught anywhere, so `rfc-ingest` shows a
traceback for it.

## Goals / Non-Goals

**Goals:**

- One base class to catch, one class per failure kind, and messages that are shown as they are.
- No output from library code, and one line on stderr from a command.
- Keep the messages' wording. The changes are where a message is printed and how many times.

**Non-Goals:**

- Changing `QueryResponse`, `QueryErrorCode` or the code each failure maps to.
- Adding argument checks to functions that don't check today. A wrong type passed to an unchecked
  function fails in Python's own way, which is already a `TypeError` or `AttributeError`.
- `search` with a `limit` below 1 still returns no results, as it does today.
- `logging`. Nothing in the library has anything to report except a failure, which it raises.
- `scripts/update_architecture.py`, which is a release script with its own `ArchitectureError`.
- Handling `KeyboardInterrupt` in the commands.

## Decisions

### One module of error classes

`src/rfc_qa/errors.py` holds every class:

```python
class RfcQaError(Exception):
    """A failure the user or the environment caused, with a message ready to show."""

class ConfigError(RfcQaError): ...            # missing directory, unreadable or invalid file
class DownloadError(RfcQaError): ...          # an RFC couldn't be downloaded or stored
class IngestError(RfcQaError): ...            # the corpus couldn't be turned into chunks
class IndexUnavailableError(RfcQaError): ...  # the index is missing or can't be read
class IndexBuildError(RfcQaError): ...        # the index couldn't be written
class ModelUnavailableError(RfcQaError): ...  # Ollama didn't respond
class ModelResponseError(RfcQaError): ...     # Ollama or the model answered with something unusable
```

Each class gets a docstring and no body. The message is the exception's only argument, so `str(exc)`
is the message, as for built-in exceptions. There are no extra fields such as a path or an RFC
number: nothing reads them, and the message already names them.

The modules import from `rfc_qa.errors` and raise these classes directly. `ConfigDirError`,
`QueryConfigError` and the old classes in `answer_generator` and `ingest` are removed, not kept as
aliases, because the project isn't deployed. `ConfigError` is not also a `ValueError`. If it were,
`except ValueError` written to catch a caller bug would also catch a missing directory.

Alternatives:

- One class per module. The user rejected this, because configuration errors would stay split
  across `paths`, `query` and `ingest`.
- A single class with an error-code attribute. It would tie `errors.py` to `QueryErrorCode`, and a
  caller would have to compare codes instead of using `except`.

### Raise where the failure happens, with its cause

Each function that fails raises the specific class, using `raise ... from exc` when another exception
caused it:

- `download_rfc` raises `DownloadError` for a missing directory, a request error, a non-200 status, a
  failed check and a failed write. The temporary file is still removed in a `finally` block or an
  `except` that re-raises. On success it returns `dest_path`, including when the file was already
  there.
- `build_index` raises `IndexBuildError` and returns `None`. Its cleanup of the temporary file
  doesn't change.
- A private helper in `keyword_index` that opens the index read-only raises `IndexUnavailableError`
  when the file is missing ("Index not found: '…'. Run rfc-ingest to build it.").
  `read_metadata` and `search` raise it for a `sqlite3.Error`, with the existing "Failed to …"
  wording and `rfc-ingest` added.
- `load_corpus`, `load_config`, `load_query_config` and `resolve_config_dir` raise `ConfigError`.
- `run_ingestion` lets `DownloadError` and `IndexBuildError` propagate, because both name what
  failed. It raises `IngestError` for an RFC with no chunks, and for an `OSError` reading a stored
  RFC, which no longer reaches the user as a traceback.
- `answer_generator` raises the two model classes as now, imported from `errors`.

Callers no longer check return values, so the `if not download_rfc(...)` and `if results is None`
branches go away.

### Caller bugs are the built-in exceptions

Only the public functions that check their arguments today change, so the rule needs no new
checks:

- `download_rfc` raises `TypeError` for a number that isn't an `int`, or is a `bool`, and
  `ValueError` for one below 1. The message names the value, as now.
- `query()` raises `TypeError` for a query that isn't a `str`, before reading anything. The user
  chose this. An empty or whitespace-only string still returns `INVALID_QUERY`, because it comes from
  the user, for example `rfc-query ""`.

### `query()` maps classes to the existing codes

`query()` stays the boundary that returns a response. It catches `ConfigError` as `CONFIG_INVALID`,
`IndexUnavailableError` as `INDEX_UNAVAILABLE`, `ModelUnavailableError` as `MODEL_UNAVAILABLE` and
`ModelResponseError` as `MODEL_INVALID_RESPONSE`, each with `str(exc)` as the error string and the
timings so far. These are explicit `except` clauses, in the order the stages run.

It doesn't catch the base `RfcQaError`. The other subclasses can't happen in a query, so if one did,
that would be a bug, and it should show as one instead of being reported under the wrong code.

An index whose metadata lacks `target_chunk_tokens`, or holds a value that isn't a number, is
reported as `IndexUnavailableError`. The message names the path and says to rebuild with
`rfc-ingest`. The context-window check still returns `CONFIG_INVALID` with its existing message.

### The commands report errors in one place

A small `src/rfc_qa/cli.py` holds `report_error(message: object) -> int`. It prints `message` to
stderr and returns 1. It's the only place outside the commands' success output that writes to a
stream.

- `rfc-ingest` and `rfc-search` wrap their work in `try: ... except RfcQaError as exc: return
  report_error(exc)`.
- `rfc-query` does the same around resolving its directories. A failure response from `query()` is
  reported with `report_error(response.error_string)`.

Nothing else is caught, so a bug still shows its traceback and exits 1, as Python does. `argparse`
keeps printing its usage message and exiting with status 2, which is the convention for that kind
of error.

Alternative: a decorator that turns `RfcQaError` into an exit status. It hides control flow for
three short functions, and `rfc-query` would still need its own branch for failure responses.

### Enforce "never prints" with a test

`tests/test_errors.py` parses every module in `src/rfc_qa` with `ast`. It fails if a call to
`print`, or a use of `sys.stdout` or `sys.stderr`, appears outside the command code. The command code
is `cli.py`, the `main` functions, and the output helpers that `main` calls, such as `_print_success`,
listed by name in the test.

The scenario tests for each failure path also capture output and check that it's empty. The `ast`
test is what keeps a future `print` from slipping into the library.

## Risks / Trade-offs

- [Callers of `download_rfc`, `build_index`, `search` and `read_metadata` that check return values
  break] → The only callers are in this repository, and they change in this change. The proposal
  marks the change as breaking.
- [`query(None)` now raises instead of returning a response] → The user chose this. The README and
  the query-interface spec say so, and the error code is unchanged for empty strings.
- [The `ast` test's allow-list could drift from the code] → It lists a handful of functions by name,
  and a new output helper fails the test until it's added on purpose.
- [A message that used to be printed by a library function and then summarised by its caller is now
  shown once, so the summary goes] → For example, `IngestError("RFC 9110: download failed.")` gives
  way to the `DownloadError` message, which carries the reason as well as the RFC.
