# document_service
Document Q&amp;A Service

A retrieval-augmented generation (RAG) service that answers questions about IETF RFCs and
cites the sections its answers come from.

This is a learning project built in public. The pipeline is written by hand rather than with
a RAG framework, and each step is planned as an [OpenSpec](openspec/) change, so the proposals
and designs record what was decided, why, and which alternatives were rejected.

## Approach

- **Corpus:** a curated set of HTTP, TLS and TCP RFCs. It deliberately includes obsolete pairs,
  such as RFC 793 and RFC 9293.
- **Obsolete RFCs:** every RFC is indexed. Labeling each with its status, and preferring current
  RFCs unless a question asks for older ones, is planned for step 3. The improvement is measured
  with a stale citation rate: how often an answer cites an obsolete RFC when the question didn't
  ask for one.
- **Models:** local open-weight models served by Ollama, with `llama3.2` for generation and
  `nomic-embed-text` for embeddings. Both are configurable, and a larger model will be compared
  against this baseline.
- **Citations:** passages are labeled `P1`, `P2` and so on for the model, and code maps the labels
  it cites back to chunks, dropping any that weren't retrieved. This proves a cited passage was
  retrieved, not that it supports the answer. `llama3.2` sometimes answers a question the corpus
  doesn't cover from its own knowledge, while citing real passages. Step 2 measures how often.
- **Ingestion and querying are separate:** an offline step builds the index, and the Docker image
  contains that index for a stateless query service to use.

```
 OFFLINE (batch job)                      ONLINE (stateless service)
 download --> parse --> chunk --> index   query --> retrieve --> generate --> cite
                                    |                  ^
                                    +--- index store --+
```

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
