# document_service
Document Q&amp;A Service

A retrieval-augmented generation (RAG) service that answers questions about IETF RFCs and
cites the sections its answers come from.

This is a learning project built in public. The pipeline is written by hand rather than with
a RAG framework, and each step is planned as an [OpenSpec](openspec/) change, so the proposals
and designs record what was decided, why, and which alternatives were rejected.

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
  temporary file and renames it into place. Ingestion reuses any RFC file already in `data/`, so an
  interrupted download never leaves a broken file to be indexed later.
- **The problem worth solving.** I scoped the corpus to HTTP, TLS and TCP, and chose status-aware
  retrieval as the goal, so that answers don't rely on RFCs that have been replaced. That's why the
  corpus deliberately includes obsolete RFCs alongside the ones that replaced them.
- **Building it by hand.** I chose to write the pipeline without a RAG framework, and to run
  open-weight models locally with Ollama, so that each part can be seen and understood.
- **Two entry points.** The split of the system into an offline ingestion step, `ingest.py`, and a
  query step, `query.py`, came out of my planning discussions with the agents. Separating them means
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

The project uses Python 3.14. To install the dependencies and run the tests:

```
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
```

Use `python -m pytest` rather than bare `pytest`, because the modules sit at the repository root.
The network integration test is skipped unless `RFC_DOWNLOADER_NETWORK_TESTS=1` is set.

Changes reach `main` through pull requests. GitHub Actions runs the tests on each pull request
and on each push to `main`, without network access to external document sources, and a pull
request can't merge until they pass.

Each change is reviewed, then archived on its branch, then merged, so that the code, spec and
archive land as one commit. The `archive-check` check enforces this by failing while a pull request
adds or modifies files in an active OpenSpec change, so it's expected to fail during review. If a
change has work that can only happen after merge, the `merge-before-archive` label passes this
check. It doesn't affect any other check, so the tests must still pass.

## Building the index

Ingestion downloads any missing RFCs into `data/`, then builds the search index at `data/index.db`.
The first run needs network access to rfc-editor.org. `data/` is generated, so it isn't committed.

```
python ingest.py
```

To search the index from the command line:

```
python keyword_index.py "three-way handshake"
python keyword_index.py "Content-Length" --limit 3
```

[`corpus.json`](corpus.json) lists the RFCs, with their family and title.
[`ingest_config.json`](ingest_config.json) sets the chunk size limit:

- `embedding_model` is the embedding model and its token limit, which is the hard ceiling.
- `target_chunk_tokens` is the chunk size to aim for inside that ceiling.
- `chars_per_token` is measured for this corpus with this model's tokenizer, so measure it again
  if either one changes.

The maximum chunk size in characters is `target_chunk_tokens` x `chars_per_token`. The index
records the configuration that built it.

## Asking a question

Answering needs [Ollama](https://ollama.com) running locally with the `llama3.2` model, and an index
built by `ingest.py`:

```
ollama pull llama3.2
python query.py "What does a 404 status code mean?"
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
that happened. From Python, `query.query()` returns the same result, with timings and a
`cold_start` flag, so that slow first answers can be left out of performance figures.

[`query_config.json`](query_config.json) sets the model, the Ollama address, the context window,
the answer length limit, the request timeout and how many passages to retrieve. A query fails before
calling the model if those passages and the answer wouldn't fit in the context window.

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

The code is released under the [MIT License](LICENSE). The test fixtures in `tests/fixtures/` contain
excerpts of RFCs, which remain under the IETF Trust's terms in [BCP 78](https://www.rfc-editor.org/info/bcp78).
RFCs downloaded by ingestion aren't committed.
