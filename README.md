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
- **Obsolete RFCs:** every RFC is indexed and labeled with its status. Retrieval prefers current
  RFCs, and older ones are used only when a question asks for them. The improvement is measured
  with a stale citation rate: how often an answer cites an obsolete RFC when the question didn't
  ask for one.
- **Models:** local open-weight models served by Ollama, with `llama3.2` for generation and
  `nomic-embed-text` for embeddings. Both are configurable, and a larger model will be compared
  against this baseline.
- **Citations:** the model cites chunk IDs, and code rejects any ID that wasn't retrieved.
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

## Roadmap

The RFC downloader, the top-level query interface and basic CI are complete. A valid query currently
returns `NOT_IMPLEMENTED` until the steps below are built.

```
 [0] Basic CI (complete)
  |
 [1] Walking skeleton: parse + chunk + keyword search + LLM + citations
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
- The exact list of RFCs in the corpus.
- Chunk size, given the 2,048-token limit of the embedding model.
