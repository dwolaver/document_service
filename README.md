# rfc-qa

RFC Q&A: cited answers from the IETF RFCs.

A retrieval-augmented generation (RAG) service that answers questions about IETF RFCs and
cites the sections its answers come from.

This is a portfolio project, developed in the open. The pipeline is written by hand rather than
with a RAG framework, so each stage can be inspected and measured. Each step is planned as an
[OpenSpec](openspec/) change, so the proposals and designs record what was decided, why, and which
alternatives were rejected.

## How this was built

I didn't write the code in this repository. AI coding assistants wrote it, along with the tests and
the OpenSpec proposals, designs, task lists and specs: GitHub Copilot the first two components, and
Claude, in Claude Code, everything since. My part was to direct the work and to decide what was
accepted. I set the goals, the scope and the order of the roadmap, reviewed every proposal, design,
task list and spec, and reviewed and merged every pull request myself.

Some of the decisions that shaped the result:

- **The problem worth solving.** Status-aware retrieval, so that answers don't rely on RFCs that have
  been replaced. The corpus deliberately includes obsolete RFCs alongside their replacements.
- **Testing a choice instead of assuming it.** SQLite was weighed against ChromaDB by measurement.
  Local Chroma had no BM25 ranking, so SQLite FTS5 stayed, behind two functions that a new backend
  can replace.
- **Enforcing the review order.** A change is archived on its branch before it merges, and a required
  check fails until it is, rather than relying on remembering.
- **A pinned model for the architecture document.** `ARCHITECTURE.md` is regenerated from the code at
  each release, only by one pinned model, and a script refuses the result from any other.

[How this was built](docs/how-it-was-built.md) has the full account and every decision. The record
is public: the [archived proposals and designs](openspec/changes/archive/) show each decision with
its reasons, and the [pull requests](https://github.com/dwolaver/rfc-qa/pulls?q=is%3Apr)
show the reviews.

## Approach

[ARCHITECTURE.md](ARCHITECTURE.md) describes how the system works, from an overview down to its
interfaces, with diagrams and the key decisions behind it. In short:

- A curated set of 59 HTTP, TLS and TCP RFCs, deliberately including obsolete RFCs alongside the ones
  that replaced them.
- An offline ingestion step that parses RFCs into sections and chunks, and builds a keyword index.
- A query step that retrieves passages and asks a local `llama3.2` model, served by Ollama, to answer
  only from them, with citations that code checks against what was retrieved.

## Quick start

In a virtual environment on Python 3.14, with [Ollama](https://ollama.com) running locally:

```
pip install .
ollama pull llama3.2
rfc-ingest
rfc-query "What does a 404 status code mean?"
```

`rfc-ingest` downloads the RFCs and builds the index, which needs network access the first time. The
answer is printed with its sources:

```
The origin server did not find a current representation for the target resource or is not willing to disclose that one exists.

Sources:
  RFC 9110 section 15.5.5: 404 Not Found (rfc9110-s15.5.5-p0)
  RFC 7231 section 6.5.4: 404 Not Found (rfc7231-s6.5.4-p0)
  RFC 2616 section 10.4.5: 404 Not Found (rfc2616-s10.4.5-p0)
```

## Roadmap

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

[The roadmap](docs/roadmap.md) explains the order and lists the open questions.

## Documentation

| Document | What it covers |
| --- | --- |
| [How this was built](docs/how-it-was-built.md) | Who wrote the code, what the owner directed, and every decision that shaped it |
| [ARCHITECTURE.md](ARCHITECTURE.md) | How the system works, from an overview down to its interfaces, and its key decisions |
| [Usage](docs/usage.md) | Installing, building the index, searching, asking a question, `-v`, and exit statuses |
| [Configuration](docs/configuration.md) | The configuration files, the query settings, and choosing the configuration and data directories |
| [Using the library](docs/library.md) | Calling the package from Python: `query()`, the errors it raises, and logging |
| [Roadmap](docs/roadmap.md) | The steps ahead, why they're in that order, and the open questions |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setting up, the tests, the lint, type and secret checks, and how a change reaches `main` |
| [Releasing](docs/releasing.md) | The release steps, including updating `ARCHITECTURE.md` |
| [CHANGELOG.md](CHANGELOG.md) | What changed in each release, and what's changed since the last one |
| [SECURITY.md](SECURITY.md) | Supported versions, reporting a vulnerability privately, and leaked secrets |

## License

The code is released under the [MIT License](LICENSE). The test fixtures in
`tests/ingestion/fixtures/` contain excerpts of RFCs, which remain under the IETF Trust's terms in
[BCP 78](https://www.rfc-editor.org/info/bcp78). RFCs downloaded by ingestion aren't committed.
