# Proposal

## Why

The project can now build a searchable index of RFC passages, but `query()` still returns
`NOT_IMPLEMENTED`. This change connects the two halves of the pipeline, so that a question gets an
answer from a local model with citations to the RFC sections it came from. That completes roadmap
step 1, and it gives step 2's golden question set something to measure.

## What Changes

- Retrieve passages for a question from the keyword index, then ask the local `llama3.2` model
  through Ollama to answer using only those passages.
- Return structured answers: the model reports whether the passages answer the question, gives the
  answer, and names the passages it used.
- Check citations in code. Passages are labeled `P1`, `P2` and so on, and code maps the labels back
  to chunk IDs. Labels that weren't retrieved are dropped.
- Treat a question the RFCs don't answer as a successful response that says so, with no citations.
  This covers no search results, the model reporting not found, and an answer with no valid
  citations.
- **BREAKING**: A valid query no longer returns `NOT_IMPLEMENTED`. The `QueryResponse` gains `found`,
  `citations` and `timings`, and `QueryErrorCode` gains codes for an unavailable index, an unavailable model,
  an invalid model response, and invalid configuration.
- Add `query_config.json` for the model, Ollama address, context window, timeout and retrieval
  limit. Check that the retrieved passages and the answer fit the model's context window, and detect
  a prompt that Ollama cut short.
- Report timings with every answer: total, retrieval, model load and generation time, token counts,
  and a `cold_start` flag when Ollama had to load the model first. Cold starts measured about 5
  seconds against 53 ms warm, so the flag keeps them out of later performance figures.
- When the model isn't installed or Ollama isn't running, fail with a hint saying how to fix it.
  Queries never download a model or start Ollama.
- Print the answer and its citations from the console command, with a note when the model was loaded
  for that query.
- Update the README to mark step 1 complete and to show how to ask a question.

Out of scope: preferring current RFCs over obsolete ones and embeddings, which belong to step 3, and
the golden question set, which belongs to step 2. Proving that an answer is supported by its
citations is also out of scope: testing showed that `llama3.2` can invent an answer and cite real
passages, and step 2 will measure how often.

## Capabilities

### New Capabilities
- `answer-generation`: Producing a cited answer from retrieved RFC passages, including the prompt,
  the model call, citation checks, not-found handling, configuration and model failures.

### Modified Capabilities
- `query-interface`: The response gains `found`, `citations` and `timings`, the not-implemented
  requirement is removed, and the console prints citations and a cold-start note.

## Impact

- New: `answer_generator.py`, `query_config.json`, and their tests.
- Updated: `query.py`, `tests/test_query.py`, `pytest.ini` and `README.md`.
- No new dependencies. Ollama is called through its HTTP API with `requests`, which the project
  already uses.
- Answering needs Ollama running locally with `llama3.2`, and an index built by `ingest.py`. Tests
  and CI stay offline by replacing the model call.
