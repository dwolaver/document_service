# Using the library

[Back to README](../README.md)

The commands in [Usage](usage.md) are thin layers over the `rfc_qa` package, which can also be called
from Python. The package is installed by `pip install .`, or in editable mode for development, as
described in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Asking a question

`rfc_qa.query.query()` returns the same result as `rfc-query`, with timings and a `cold_start` flag,
so that slow first answers can be left out of performance figures.

`query(question, config_dir=..., data_dir=...)` takes either directory ahead of its variable, which
otherwise chooses it as described in [Configuration](configuration.md).

## Handling errors

The library never prints. A failure caused by the user, the configuration or the environment raises
an error from [`rfc_qa.errors`](../src/rfc_qa/errors.py), and `str()` of it is a message ready to
show. Every one is an `RfcQaError`, so one `except` catches them all, and each kind has its own
subclass: `ConfigError`, `DownloadError`, `IngestError`, `IndexUnavailableError`, `IndexBuildError`,
`ModelUnavailableError` and `ModelResponseError`. When another exception caused the failure, such as
a network or database error, it's the error's `__cause__`.

A mistake in the calling code raises the built-in `TypeError` or `ValueError` instead, which
`except RfcQaError` doesn't catch. For example, `download_rfc("9110", ...)` raises `TypeError`, and
`download_rfc(0, ...)` raises `ValueError`.

`query()` is the exception. It returns a `QueryResponse` for every expected failure, with an
`error_code` and the error's message as its `error_string`, and only raises `TypeError` for a query
that isn't a string. An empty query is user input, so it's returned as `INVALID_QUERY`.

```python
from rfc_qa.errors import IndexUnavailableError
from rfc_qa.query import query
from rfc_qa.retrieval.keyword_index import search

try:
    search("/nonexistent/index.db", "404 Not Found")
except IndexUnavailableError as exc:
    print(exc)  # Index not found: '/nonexistent/index.db'. Run rfc-ingest to build it.

response = query("What does a 404 status code mean?", data_dir="/nonexistent")
if not response.success:
    print(response.error_code.name)  # INDEX_UNAVAILABLE
```

The commands report these errors as described in [Errors and exit
statuses](usage.md#errors-and-exit-statuses).

## Seeing what the library is doing

The library's records come from Python's `logging` module, on loggers named after each module under
`rfc_qa`. The library never configures logging itself, so a program that uses it sees nothing until
it does. To see the library's progress without other libraries' records, configure logging as usual
and set the level of the `rfc_qa` logger:

```python
import logging
import tempfile

from rfc_qa.ingestion.rfc_downloader import download_rfc

logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("rfc_qa").setLevel(logging.INFO)

with tempfile.TemporaryDirectory() as directory:
    download_rfc(791, directory)
# INFO rfc_qa.ingestion.rfc_downloader: Downloading RFC 791 from https://www.rfc-editor.org/rfc/rfc791.txt
```

Failures are raised, not logged, so a program that logs the library's records still handles errors
as described above. The commands show the same records with `-v`, as described in [Seeing what the
commands are doing](usage.md#seeing-what-the-commands-are-doing).
