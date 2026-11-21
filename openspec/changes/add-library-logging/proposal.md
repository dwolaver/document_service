# Proposal

## Why

The library has no `print()` calls left to convert. Since the error-handling change, it never writes
output: failures are raised, and only the commands print. But it also has no way to say what it's
doing. A slow `rfc-ingest` gives no sign of which RFC it's downloading. A query that returns "not
found" doesn't show which passages were retrieved or how long the model took. And a program that
embeds the library can't see what's happening without reading the code. Python's `logging` module
is the standard way to report this: the library emits records, and the application decides whether
and where they're shown.

## What Changes

- Each library module that does I/O or calls the model gets a module logger
  (`logging.getLogger(__name__)`, so all are under `rfc_qa`). It logs what it's doing:
  - `INFO` for progress a user would want to see, such as a download starting, the corpus being
    chunked, the index being written, and passages being retrieved and answered.
  - `DEBUG` for detail, such as the directories selected and where each came from, an RFC that was
    already stored, each search and its result count, and the model's token counts.
- The library never configures logging. The `rfc_qa` package logger gets a `NullHandler`, so a
  program that hasn't set up logging sees nothing, as today. Failures are still raised, not logged,
  so an error isn't reported twice.
- `rfc-ingest`, `rfc-search` and `rfc-query` accept `-v`/`--verbose`. `-v` shows `INFO` records and
  `-vv` adds `DEBUG`, written to standard error so standard output still holds only results. Without
  the flag, the output is exactly what it is today.
- The lint rules add ruff's logging checks (`LOG` and `G`), which report, for example, a log message
  built with an f-string instead of logging's own arguments, or a call on the root logger.
- The release script `scripts/update_architecture.py` keeps printing its report. It's a command, not
  library code.

## Capabilities

### New Capabilities

- `diagnostic-logging`: what the library logs and at which level, that it never configures logging or
  shows anything by default, and how the commands' `-v` flag shows its records.

### Modified Capabilities

- `error-handling`: "Never print from library code" says the library reports what it's doing only
  through logging. "Report errors once from the commands" keeps an error as one line on standard
  error, and with `-v` the log records come before it.
- `query-interface`: the console's failure output is the only output on standard error when it's
  run without `-v`.
- `code-quality`: the lint rules include the checks for logging calls.

## Impact

- Code:
  - `src/rfc_qa/__init__.py` adds the `NullHandler`.
  - Loggers are added to `paths.py`, `ingestion/rfc_downloader.py`, `ingestion/ingest.py`,
    `retrieval/keyword_index.py`, `query.py` and `generation/answer_generator.py`.
  - `cli.py` adds the `-v` argument and the handler setup, and the three `main()` functions use it.
  - `rfc_parser.py` and `chunker.py` stay pure functions without logging. Their results are
    logged by `ingest`.
- Configuration: `pyproject.toml` adds `LOG` and `G` to the selected lint rules.
- Behavior: none without `-v`. The never-prints test stays as it is, because logging writes
  through a handler that only the commands attach.
- README: how to use `-v`, and how a Python caller can show the library's log records.
