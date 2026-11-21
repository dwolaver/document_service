# Design

## Context

- **No output from the library today:** it writes nothing. `tests/test_errors.py` parses
  `src/rfc_qa` and fails on any `print`, `sys.stdout` or `sys.stderr` outside `cli.py`, the `main`
  functions and `query._print_success`.
- **No logging today:** nothing in the project uses `logging`.
- **Where the commands are:** each command's `main()` lives in its library module
  (`ingest.py`, `keyword_index.py`, `query.py`). They share `cli.report_error`.
- **Output streams:** standard output carries each command's result (the summary, the matches, or
  the answer and sources). Standard error carries one line per failure. The specs and tests rely on
  both.
- **Where a user waits:** downloads in `rfc-ingest` (59 RFCs on a fresh data directory), and the
  model call in `rfc-query`.

## Goals / Non-Goals

**Goals:**

- The library emits log records that are useful to a user following progress and to someone
  diagnosing a problem.
- Nothing changes for anyone who doesn't ask for the records.
- The same records serve the commands' `-v` and a program that embeds the library.

**Non-Goals:**

- **No new places to send records:** no log files, JSON output or log configuration files. A program
  that wants them uses `logging` itself.
- **Errors aren't logged:** they stay raised and are printed once by the commands.
- **Other libraries' records aren't shown:** `requests` and `urllib3` stay silent even with `-vv`.
- **The release script is unchanged:** `scripts/update_architecture.py` is a command and keeps
  printing its report.
- **The command code stays where it is:** moving `main()` out of the library modules isn't part of
  this change.
- **Parser and chunker:** `rfc_parser` and `chunker` stay pure functions without logging. `ingest`
  logs their results.

## Decisions

### One logger per module, under `rfc_qa`

Each module that logs starts with `logger = logging.getLogger(__name__)`. That gives names like
`rfc_qa.ingestion.rfc_downloader`, so a program can tune one module or the whole package. Calls pass
values as arguments, for example `logger.info("Downloading RFC %d from %s", number, url)`. The message
is then only formatted when a handler will show it, and the record keeps its arguments.

`src/rfc_qa/__init__.py` adds `logging.getLogger("rfc_qa").addHandler(logging.NullHandler())`, as the
logging documentation recommends for libraries. Without it, Python's last-resort handler would print
any `WARNING` the library emits to standard error. The library only logs `INFO` and `DEBUG` today,
but the handler keeps it silent if a warning is added later.

Alternative: a single `rfc_qa` logger for every module. It's simpler, but a program couldn't turn up
the detail for one area, such as the model calls, without the rest.

### What each module logs

The records name what they're about, the way the error messages do. Paths use `%r`, so they show in
quotes as in the errors.

| Module | `INFO` | `DEBUG` |
| --- | --- | --- |
| `paths` | | the configuration and data directory selected, and their source |
| `ingestion.rfc_downloader` | downloading RFC *n* from its URL | RFC *n* already stored at a path; stored *b* bytes at a path |
| `ingestion.ingest` | *n* RFCs in the manifest; chunked *n* RFCs into *c* chunks | RFC *n*: *s* sections, *c* chunks |
| `retrieval.keyword_index` | writing *c* chunks to the index at a path | a search's query, limit and result count |
| `query` | retrieved *n* passages in *t* ms; the model found an answer, or didn't, in *t* ms | the configuration file and index used; the context budget |
| `generation.answer_generator` | | the model and address called, and the number of passages; the prompt and answer token counts, and the load and generation times |

The query text appears in `DEBUG` search records, and in no `INFO` record. Neither the prompt sent to
the model nor its raw response is logged. They're long, and the answer is already the command's
output.

### Errors stay raised

A function that raises doesn't also log the failure. If it did, `rfc-ingest -v` would show the error
twice: once as a record and once from `report_error`, which is the double reporting the last change
removed. Records before a failure, such as "Downloading RFC 9110 …", still show where the failure
happened.

### `-v` in the commands, set up in `cli.py`

`cli.py` gains two helpers that each command's `main()` calls:

- `add_verbose_argument(parser)` adds `-v`/`--verbose` with `action="count"`.
- `configure_logging(verbosity)`:
  - With a verbosity of 0, it does nothing.
  - Otherwise it attaches one `StreamHandler(sys.stderr)` to the `rfc_qa` logger, with the format
    `%(levelname)s %(name)s: %(message)s`, and sets the logger's level to `INFO` for 1 or `DEBUG` for
    2 or more.
  - It keeps a reference to the handler it added and replaces it on a later call. Tests call `main()`
    many times in one process, so handlers mustn't pile up.

The root logger isn't touched, so other libraries stay silent. A record line has a level prefix,
which distinguishes it from the unprefixed error line that `report_error` prints last.

Alternative: `logging.basicConfig(level=...)`. It configures the root logger, which would show
`urllib3`'s connection records at `-vv` and would apply to a program that calls `main()`.

### Lint the logging calls

`pyproject.toml` adds ruff's `LOG` (flake8-logging) and `G` (flake8-logging-format) to `select`. They
report, for example:

- `G004`: an f-string message.
- `G001` and `G002`: a message built with `str.format()` or `%`.
- `LOG015`: a call on the root logger.

None of them reports anything in the code today. `UP031` doesn't conflict: it only reports `%` used
as an operator on a string, not `%s` placeholders passed to a logger.

### Tests

- **Library records:** tests use pytest's `caplog`, at `DEBUG`, on the main paths:
  - a download and a skipped download;
  - an ingestion run;
  - a search;
  - a query that's answered and one that isn't found;
  - the selected directories.

  They check each record's logger name, level, and the values its message names.
- **Not logged:** a failing download and a missing index produce no record that repeats the error's
  message. Without configuration, `capsys` stays empty, which the existing scenario tests already
  check.
- **Commands:** for each command:
  - `-v` writes `INFO` lines and no `DEBUG` lines to standard error, and standard output is
    unchanged.
  - `-vv` adds `DEBUG` lines.
  - Without the flag, standard error is empty on success.
  - With `-v`, a failure ends standard error with the error's message, which appears once.
- **The handler doesn't pile up:** after two calls of `main(["-v", …])`, the `rfc_qa` logger has one
  handler that `cli` added.
- **Never-prints test:** it's unchanged and still passes, because the only stream reference is in
  `cli.py`.

Each test that sets up logging restores the `rfc_qa` logger's level and handlers afterwards, through
a fixture in `conftest.py`, so tests stay independent.

## Risks / Trade-offs

- **Records add noise over time** → New records follow the same split: `INFO` is what a user
  waiting on a command wants, and everything else is `DEBUG`. The table above is the reference.
- **A record leaks something private** → The project handles public RFCs and the user's own
  question. The question only goes into `DEBUG` records, which are off unless asked for, and nothing
  is written to a file.
- **`configure_logging` changes global logging state** in a program that calls a command's `main()`
  → It only touches the `rfc_qa` logger, only when `-v` is given, and replaces its own handler rather
  than adding another.
- **An existing test assumes an empty standard error** → Without `-v` nothing changes, so these tests
  keep passing as they are.
