# Roadmap

[Back to README](../README.md)

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

## Open questions

- How the LLM runs in the cloud: a GPU node, a small CPU model, or a hosted API.
- Chunk size, given the 2,048-token limit of the embedding model.

