# Usage

[Back to README](../README.md)

The project installs three commands: `rfc-ingest` builds the search index, `rfc-search` searches it,
and `rfc-query` answers a question from it. They work from any directory. Where the commands read
their settings and keep their data is described in [Configuration](configuration.md), and calling
the package from Python in [Using the library](library.md).

## Installing

To use the commands without working on the code, install the project normally into a virtual
environment on Python 3.14, either from a clone or from a wheel built from one:

```
pip install .
```

```
pip wheel --no-deps -w dist .
pip install dist/rfc_qa-0.1.0-py3-none-any.whl
```

The commands then work from any directory, and the clone can be removed: the default configuration
is installed with the package, and generated data goes in the user data directory. To work on the
code instead, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Building the index

Ingestion downloads any missing RFCs into the data directory, then builds the search index there as
`index.db`. By default the data directory is your user data directory for `rfc-qa`:
`~/.local/share/rfc-qa` on Linux (or under `$XDG_DATA_HOME` if that's set), `~/Library/Application
Support/rfc-qa` on macOS and `%LOCALAPPDATA%\rfc-qa` on Windows. `--help` shows the path for your
system. The first run needs network access to rfc-editor.org.

```
rfc-ingest
```

To use another data directory, or another configuration, see [Choosing the data
directory](configuration.md#choosing-the-data-directory) and [Choosing the configuration
directory](configuration.md#choosing-the-configuration-directory).

## Searching the index

To search the index from the command line:

```
rfc-search "three-way handshake"
rfc-search "Content-Length" --limit 3
```

`rfc-search` reads `index.db` from the data directory, chosen with `--data-dir` or `RFC_QA_DATA_DIR`
in the same way as for `rfc-ingest`. `--index` names a single index file instead, and takes
precedence over the data directory.

## Asking a question

Answering needs [Ollama](https://ollama.com) running locally with the `llama3.2` model, and an index
built by `rfc-ingest`:

```
ollama pull llama3.2
rfc-query "What does a 404 status code mean?"
```

The answer is printed with its sources:

```
The origin server did not find a current representation for the target resource or is not willing to disclose that one exists.

Sources:
  RFC 9110 section 15.5.5: 404 Not Found (rfc9110-s15.5.5-p0)
  RFC 7231 section 6.5.4: 404 Not Found (rfc7231-s6.5.4-p0)
  RFC 2616 section 10.4.5: 404 Not Found (rfc2616-s10.4.5-p0)
```

When the indexed RFCs don't answer a question, it says so and exits normally. Ollama loads the model
on the first question after it has been idle, which takes a few seconds, and the output notes when
that happened.

`rfc-query` chooses its configuration and data directories in the same way as `rfc-ingest`, as
described in [Configuration](configuration.md). The model, the Ollama address and the other query
settings are in [Query settings](configuration.md#query-settings).

```
rfc-query --config-dir staging "What does a 404 status code mean?"
rfc-query --data-dir /srv/rfc-qa/data "What does a 404 status code mean?"
```

## Seeing what the commands are doing

Each command takes `-v` to show its progress on standard error, and `-vv` to show details as well,
such as the directories it chose and where each choice came from. Standard output stays the same, so
`-v` can be added to a command whose output is piped somewhere. Without the flag, nothing extra is
printed.

```
$ rfc-ingest -v --data-dir /srv/rfc-qa
INFO rfc_qa.ingestion.ingest: 59 RFCs in the manifest '.../rfc_qa/config/corpus.toml'
INFO rfc_qa.ingestion.rfc_downloader: Downloading RFC 9110 from https://www.rfc-editor.org/rfc/rfc9110.txt
INFO rfc_qa.ingestion.ingest: Chunked 59 RFCs into 5261 chunks
INFO rfc_qa.retrieval.keyword_index: Writing 5261 chunks to the index at '/srv/rfc-qa/index.db'
Indexed 59 RFCs into 5261 chunks. Largest chunk: 1760 characters.
```

`rfc-query -v` shows how many passages were retrieved and how long the model took. With `-vv` it also
shows the configuration file, the index, the context budget and the model's token counts. A search
only logs details, so `rfc-search` needs `-vv`. When a command fails, the error is still printed
once, as the last line.

## Errors and exit statuses

The commands print an error's message as one line on standard error and exit with status 1. Any
other exception is a bug, so it isn't caught and shows its traceback. A command-line mistake, such as
an unknown option, prints the usage message and exits with status 2.
