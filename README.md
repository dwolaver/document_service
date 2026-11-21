# document_service
Document Q&amp;A Service

A retrieval-augmented generation (RAG) service that answers questions about IETF RFCs and
cites the sections its answers come from.

This is a portfolio project, developed in the open. The pipeline is written by hand rather than
with a RAG framework, so each stage can be inspected and measured. Each step is planned as an
[OpenSpec](openspec/) change, so the proposals and designs record what was decided, why, and which
alternatives were rejected.

## Approach

[ARCHITECTURE.md](ARCHITECTURE.md) describes how the system works, from an overview down to its
interfaces, with diagrams and the key decisions behind it. In short:

- A curated set of 59 HTTP, TLS and TCP RFCs, deliberately including obsolete RFCs alongside the ones
  that replaced them.
- An offline ingestion step that parses RFCs into sections and chunks, and builds a keyword index.
- A query step that retrieves passages and asks a local `llama3.2` model, served by Ollama, to answer
  only from them, with citations that code checks against what was retrieved.

## How this was built

I didn't write the code in this repository. AI coding assistants wrote it, along with the tests and
the OpenSpec proposals, designs, task lists and specs:

- GitHub Copilot wrote the first two components, the RFC downloader and the query interface. I
  already used Copilot in my professional work.
- I then switched to Claude, Anthropic's AI model, in Claude Code, to gain experience with it. Claude
  wrote everything since, including `ARCHITECTURE.md`. It also proposed options and their
  trade-offs, ran the measurements the designs rely on, and pointed out problems it found along the
  way.

My part was to direct the work and to decide what was accepted:

- I set the goals, the scope and the order of the roadmap.
- I reviewed every proposal, design and task list before implementation started, and every resulting
  spec before it was archived, and asked for changes where they didn't match what I wanted.
- I reviewed every pull request and merged each one myself. Branch rules require a pull request for
  every change to `main`.

These decisions were mine, and they shaped the result:

- **A narrow input from the start.** The first RFC downloader specification accepted either an
  integer or a string such as `"RFC 9110"`, `"9110"`, `"0002"` or `"RFC2"`. Before any code was
  written, I narrowed it to one positive integer, the RFC number. That removed string parsing, prefix
  and zero handling from the design, and the number goes straight into the URL and the filename.
- **Never using a partial download.** I asked for the RFC downloader to check each download before
  keeping it and to write files atomically. It rejects an empty body, a body shorter than its
  `Content-Length`, or text that doesn't identify itself as the requested RFC. Then it writes to a
  temporary file and renames it into place. Ingestion reuses any RFC file already in the data directory, so an
  interrupted download never leaves a broken file to be indexed later.
- **The problem worth solving.** I scoped the corpus to HTTP, TLS and TCP, and chose status-aware
  retrieval as the goal, so that answers don't rely on RFCs that have been replaced. That's why the
  corpus deliberately includes obsolete RFCs alongside the ones that replaced them.
- **Building it by hand.** I chose to write the pipeline without a RAG framework, and to run
  open-weight models locally with Ollama, so that each part can be seen and understood.
- **Two entry points.** The split of the system into an offline ingestion step, `rfc-ingest`, and a
  query step, `rfc-query`, came out of my planning discussions with the agents. Separating them means
  the slow work of downloading, parsing and indexing RFCs happens once, and each question works from
  the finished index.
- **Challenging the database choice.** During planning I asked for SQLite to be weighed against
  ChromaDB, and whether the database should sit behind an interface that could be swapped later. The
  comparison was tested rather than assumed. Local Chroma had no BM25 ranking, so SQLite FTS5 stayed.
  Callers reach search through two functions, so the backend can change without touching them, and a
  formal interface waits until a second backend shows what shape it needs.
- **Values tied to the models and the corpus.** Early designs hard-coded values that were only true
  for the current LLM, embedding model and corpus. I judged that short-sighted, because changing any
  of them would mean refactoring. The design was changed so that those values follow what they depend
  on, in configuration. Chunk size comes from the embedding model's token limit and a
  characters-per-token ratio measured on this corpus, and the index records the settings that built
  it. The LLM's context window and answer length are set with the model, and a query that wouldn't
  fit is refused before the model is called.
- **How answers behave.** I decided that when the RFCs don't answer a question, the result is a
  successful "not found" answer, not an error. I chose short passage labels for citations after
  comparing the trade-offs. I also asked for slow first answers, while the model loads, to be flagged,
  so that they won't skew later performance measurements.
- **Compatibility after release.** I decided that error code values could be reused before the first
  release, and must be retired rather than reused after it.
- **The review process.** I asked for every change to go through a pull request, and decided that a
  change is archived on its branch before it merges, so that the code, spec and archive land as one
  commit. Early on, I merged a pull request before archiving its change. Rather than rely on
  remembering next time, I judged that the order should be enforced, and asked for a required check
  that fails until the change is archived, with a label for genuine exceptions.
- **ARCHITECTURE.md.** The idea of a definitive architecture document, and the method for producing
  it, were mine. The source code is the ground truth, not the plans. The file goes from a high-level
  overview down to the interfaces, and is generated once and then updated, with every claim checked
  against the code. I decided that updating it is part of each release, not an OpenSpec change,
  because it describes the code as released rather than proposing anything.
- **A pinned model.** I set the goal that one model, pinned in the skill, produces the file, and that
  a run refuses to go ahead on any other. Switching models should be a deliberate decision that gets
  a more thorough review. Claude Code skills can't yet refuse to run on the wrong model, so I asked
  for a small script to enforce it, with comments saying it can be removed once they can.
- **Key decisions to revisit.** I asked for a table of key decisions, each with the assumption that
  could make it wrong, so that they can be reviewed as things change. Only I mark a decision as
  reviewed, and I reviewed and marked all 15 for v0.1.0.

The record is public. The proposals and designs in [openspec/changes/archive/](openspec/changes/archive/)
show each decision with its reasons and the alternatives that were rejected, and the
[pull requests](https://github.com/dwolaver/document_service/pulls?q=is%3Apr) show the reviews.

## Development

The project uses Python 3.14. To install the dependencies and the project's commands, and run the
tests:

```
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

`requirements-dev.txt` installs the project in editable mode, which provides the `rfc-ingest`,
`rfc-query` and `rfc-search` commands. After pulling a change to `pyproject.toml`, run the `pip
install` line again. The code lives in the `rfc_qa` package in `src/`, with a subpackage each for
ingestion, retrieval and generation. The default configuration is in `src/rfc_qa/config/`, and
generated data goes in the user data directory, as described in [Building the
index](#building-the-index). The commands find both from any directory.

The package is only imported as installed, never from the checkout. The commands, the tests and
module runs such as `python -m rfc_qa.query` all need an install, editable or regular. An install
made before the package moved to `src/` still points at the old `rfc_qa/` directory, so run the `pip
install` line again once after pulling that change.

The network integration test is skipped unless `RFC_DOWNLOADER_NETWORK_TESTS=1` is set. The
real-model test is skipped unless `OLLAMA_TESTS=1` is set. It needs Ollama with `llama3.2`, and an
index in the default data directory, or in the one `RFC_QA_DATA_DIR` names. The install tests are
skipped unless `RFC_QA_INSTALL_TESTS=1` is set. They build a wheel, install it with its dependencies
into a fresh virtual environment, and run the three commands from an empty directory, so they need
access to PyPI. CI runs them.

The code is linted and formatted with [ruff](https://docs.astral.sh/ruff/) and type-checked with
[mypy](https://mypy-lang.org/), both configured in `pyproject.toml`. A pre-commit hook runs these
checks before each commit, along with a [gitleaks](https://github.com/gitleaks/gitleaks) scan of the
staged changes for secrets. Install it once per clone:

```
pre-commit install
```

The hook runs the tools from the virtual environment, so activate it before committing. To run the
checks on every file, and to fix what ruff can fix:

```
pre-commit run --all-files
ruff format
ruff check --fix
```

The hook only reports problems, and never changes files. mypy runs in strict mode for the `rfc_qa`
package in `src/` and `scripts/`, so every function there needs complete annotations. Tests don't need
annotations, but mypy still checks the bodies of test functions, including `None` handling. A
`# type: ignore` has to name the error it suppresses, such as `# type: ignore[arg-type]`, and mypy
reports one that isn't needed.

pre-commit builds gitleaks from the version pinned in `.pre-commit-config.yaml` the first time the hook
runs, which takes a few seconds and needs network access once. Nothing else needs installing. A
finding stops the commit and shows the file, line and kind of secret, with the value redacted.

The repository is public, so a secret that reaches a commit, or is pushed, has to be treated as
leaked. Rotate it with whoever issued it, as well as removing it from the code. If a finding has been
reviewed and isn't a secret, add the fingerprint from the report, exactly as printed, as a line in
`.gitleaksignore` at the repository root. Only that finding is ignored.

Changes reach `main` through pull requests. On each pull request and each push to `main`, GitHub
Actions runs three checks, without network access to external document sources:

- `test` runs the tests.
- `quality` runs the same lint, format and type checks as the pre-commit hook.
- `secrets` scans every commit the pull request adds, or every commit pushed, with the same gitleaks
  version as the hook. A secret added in one commit and deleted in a later one still fails it.

A pull request can't merge until all three pass, so skipping the hook doesn't get unchecked code or a
secret onto `main`.

Each change is reviewed, then archived on its branch, then merged, so that the code, spec and
archive land as one commit. The `archive-check` check enforces this by failing while a pull request
adds or modifies files in an active OpenSpec change, so it's expected to fail during review. If a
change has work that can only happen after merge, the `merge-before-archive` label passes this
check. It doesn't affect any other check, so the tests must still pass.

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
is installed with the package, and generated data goes in the user data directory.

## Building the index

Ingestion downloads any missing RFCs into the data directory, then builds the search index there as
`index.db`. By default the data directory is your user data directory for `rfc-qa`:
`~/.local/share/rfc-qa` on Linux (or under `$XDG_DATA_HOME` if that's set), `~/Library/Application
Support/rfc-qa` on macOS and `%LOCALAPPDATA%\rfc-qa` on Windows. `--help` shows the path for your
system. The first run needs network access to rfc-editor.org.

```
rfc-ingest
```

To search the index from the command line:

```
rfc-search "three-way handshake"
rfc-search "Content-Length" --limit 3
```

`rfc-search` reads `index.db` from the data directory, chosen with `--data-dir` or `RFC_QA_DATA_DIR`
as described below. `--index` names a single index file instead, and takes precedence over the data
directory.

The default configuration ships inside the package, in [`src/rfc_qa/config/`](src/rfc_qa/config).
[`corpus.json`](src/rfc_qa/config/corpus.json) lists the RFCs, with their family and title.
[`ingest.json`](src/rfc_qa/config/ingest.json) sets the chunk size limit:

- `embedding_model` is the embedding model and its token limit, which is the hard ceiling.
- `target_chunk_tokens` is the chunk size to aim for inside that ceiling.
- `chars_per_token` is measured for this corpus with this model's tokenizer, so measure it again
  if either one changes.

The maximum chunk size in characters is `target_chunk_tokens` x `chars_per_token`. The index
records the configuration that built it.

To read the configuration from another directory, such as a mounted folder in a container, name it
with `--config-dir` or the `RFC_QA_CONFIG_DIR` environment variable. The flag wins over the
variable, and both win over the packaged defaults. A relative path resolves from the working
directory, and an empty variable counts as unset. A selected directory has to hold every file the
command reads: a missing file is an error, and the packaged copy isn't used instead. `--corpus` and
`--config` name a single manifest or ingestion configuration file instead, and take precedence over
the directory for that file.

In an editable install, the packaged defaults are the files in `src/rfc_qa/config/`, so edit them
there. After a regular install they're inside the installed package, which shouldn't be edited. Copy
them into a directory of your own and select it:

```
cp -r "$(python -c 'from importlib.resources import files; print(files("rfc_qa") / "config")')" my-config
rfc-ingest --config-dir my-config
```

```
RFC_QA_CONFIG_DIR=/srv/rfc-qa/config rfc-ingest
rfc-ingest --config-dir staging --corpus small-corpus.json
```

Generated data goes in one data directory: the downloaded RFCs in its `rfcs/` folder and the index in
`index.db`. To put it somewhere else, such as a mounted volume, name the directory with `--data-dir`
or the `RFC_QA_DATA_DIR` environment variable. The precedence is the same as for configuration: the
flag, then the variable, then the user data directory. `rfc-ingest` creates the directory if
it doesn't exist. `rfc-query` and `rfc-search` choose their data directory the same way, so they read
the index that `rfc-ingest` built there.

```
RFC_QA_DATA_DIR=/srv/rfc-qa/data rfc-ingest
rfc-ingest --data-dir scratch
```

The default used to be `data/` at the repository root. To keep using RFCs and an index from there,
move the folder to the user data directory, or keep it where it is and select it:

```
mv data ~/.local/share/rfc-qa
export RFC_QA_DATA_DIR="$PWD/data"
```

A configuration directory that doesn't exist stops the run before anything is downloaded, with a
message naming the directory and whether it came from the flag or the variable.

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
that happened. From Python, `rfc_qa.query.query()` returns the same result, with timings and a
`cold_start` flag, so that slow first answers can be left out of performance figures.

[`query.json`](src/rfc_qa/config/query.json) sets the model, the Ollama address, the context window,
the answer length limit, the request timeout and how many passages to retrieve. A query fails before
calling the model if those passages and the answer wouldn't fit in the context window. The index
location isn't a setting: it's always `index.db` in the data directory.

When the `OLLAMA_BASE_URL` environment variable is set and not empty, it replaces the Ollama address
from `query.json`, for example to reach Ollama in another container. The file must still give an
address of its own. If Ollama can't be reached, the error names the address that was tried, which
shows when a leftover variable is redirecting queries.

```
OLLAMA_BASE_URL=http://ollama:11434 rfc-query "What does a 404 status code mean?"
```

`rfc-query` reads its configuration from `--config-dir`, then `RFC_QA_CONFIG_DIR`, then the packaged
defaults, and its index from `--data-dir`, then `RFC_QA_DATA_DIR`, then the user data directory, in
the same way as `rfc-ingest`. From Python, `query(question, config_dir=..., data_dir=...)` takes
either directory ahead of its variable. A configuration directory that doesn't exist gives a
configuration error naming it and where it was set. A data directory without an index gives the
index error, which names the index path and says to run `rfc-ingest`.

```
rfc-query --config-dir staging "What does a 404 status code mean?"
rfc-query --data-dir /srv/rfc-qa/data "What does a 404 status code mean?"
```

## Handling errors

The library never prints. A failure caused by the user, the configuration or the environment raises
an error from [`rfc_qa.errors`](src/rfc_qa/errors.py), and `str()` of it is a message ready to show.
Every one is an `RfcQaError`, so one `except` catches them all, and each kind has its own subclass:
`ConfigError`, `DownloadError`, `IngestError`, `IndexUnavailableError`, `IndexBuildError`,
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

The commands print an error's message as one line on standard error and exit with status 1. Any
other exception is a bug, so it isn't caught and shows its traceback. A command-line mistake, such as
an unknown option, prints the usage message and exits with status 2.

## Seeing what the library is doing

Each command takes `-v` to show its progress on standard error, and `-vv` to show details as well,
such as the directories it chose and where each choice came from. Standard output stays the same, so
`-v` can be added to a command whose output is piped somewhere. Without the flag, nothing extra is
printed.

```
$ rfc-ingest -v --data-dir /srv/rfc-qa
INFO rfc_qa.ingestion.ingest: 59 RFCs in the manifest '.../rfc_qa/config/corpus.json'
INFO rfc_qa.ingestion.rfc_downloader: Downloading RFC 9110 from https://www.rfc-editor.org/rfc/rfc9110.txt
INFO rfc_qa.ingestion.ingest: Chunked 59 RFCs into 5261 chunks
INFO rfc_qa.retrieval.keyword_index: Writing 5261 chunks to the index at '/srv/rfc-qa/index.db'
Indexed 59 RFCs into 5261 chunks. Largest chunk: 1760 characters.
```

`rfc-query -v` shows how many passages were retrieved and how long the model took. With `-vv` it also
shows the configuration file, the index, the context budget and the model's token counts. A search
only logs details, so `rfc-search` needs `-vv`. When a command fails, the error is still printed
once, as the last line.

The records come from Python's `logging` module, on loggers named after each module under `rfc_qa`.
The library never configures logging itself, so a program that uses it sees nothing until it does.
To see the library's progress without other libraries' records, configure logging as usual and set
the level of the `rfc_qa` logger:

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
as described above.

## Updating ARCHITECTURE.md

`ARCHITECTURE.md` is generated from the source code just before each release, and reviewed in a pull
request. It doesn't go through the OpenSpec process. From a release branch:

```
python scripts/update_architecture.py v0.1.0
```

The script runs the `update-architecture` skill in headless Claude Code with the model pinned in
[its `SKILL.md`](.claude/skills/update-architecture/SKILL.md), and keeps the result only if that
model did the work. Otherwise it restores the file and exits with an error. Commit or discard any
edits to `ARCHITECTURE.md` first, because the script won't run over them.

The run reports the key decisions it added or flagged for review, and the assumptions it can't check
from the code. Only the repository owner marks a decision as reviewed. Changing the pinned model is a
deliberate edit to `SKILL.md`, and the next run regenerates the file for a more thorough review.

## Roadmap

Basic CI and the walking skeleton are complete, so a question gets a cited answer from keyword
search and a local model. The steps below improve and measure it, then deploy it.

```
 [0] Basic CI (complete)
  |
 [1] Walking skeleton: parse + chunk + keyword search + LLM + citations (complete)
  |
 [2] Small golden question set, including stale-citation traps
  |
 [3] Embeddings / hybrid search, then status-aware retrieval
  |
 [4] HTTP API --> [5] Docker --> [6] Cloud + CD --> [7] Observability --> [8] Kubernetes
  |
 [9] Deep evaluation (open-ended)
```

The golden set comes early so that each retrieval change can be measured against it. Deep
evaluation stays last because it is open-ended.

### Open questions

- How the LLM runs in the cloud: a GPU node, a small CPU model, or a hosted API.
- Chunk size, given the 2,048-token limit of the embedding model.

## License

The code is released under the [MIT License](LICENSE). The test fixtures in
`tests/ingestion/fixtures/` contain excerpts of RFCs, which remain under the IETF Trust's terms in
[BCP 78](https://www.rfc-editor.org/info/bcp78). RFCs downloaded by ingestion aren't committed.
