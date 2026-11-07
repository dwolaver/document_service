# Design

## Context

See proposal.md - Why. Requirements are in specs/answer-generation/spec.md and
specs/query-interface/spec.md.

`query.py` validates input, returns `NOT_IMPLEMENTED` for a valid query, and has a console wrapper.
`keyword_index.search(path, query_text, limit)` returns `SearchResult` objects, or `None` when the
index can't be read. The index metadata records `target_chunk_tokens`, which is 1,100. Ollama is
version 0.40.12, and `llama3.2` is the 3.2B model with Q4_K_M quantization, reporting a
131,072-token context.

Before writing this design, a spike ran 10 questions through the real index and `llama3.2`, using
Ollama's structured output with a `found`, `answer` and `citations` schema:

- After the model had loaded, answers took 0.5 to 1 second, with prompts of 1,000 to 1,850 tokens.
  The first call took 6.4 seconds while the model loaded.
- Natural-language questions retrieved relevant passages for the questions the corpus covers, even
  with words like `what` and `does` in them.
- Citation labels behaved very differently depending on their format:

| Labels | Answerable questions | Out-of-corpus questions |
|---|---|---|
| Full chunk IDs after an RFC header | One good answer cited the header text instead, which failed the check | Invented answers cited invented IDs, which the check caught |
| Short labels, `P1` to `P5` | All correctly formatted | DNS, BGP, SMTP and QUIC answers were invented, yet cited real labels |
| Full IDs after `Passage id:` | Every answer copied the prefix or changed the case, failing the check | Same, so nothing was found |

- Only two of the out-of-corpus questions were reported as not found: "What is the capital of
  France?" and IPv6 neighbor discovery.

A second measurement checked what happens when the model isn't loaded. Ollama unloads a model after
5 minutes idle by default, and before the test no model was loaded. The next request loaded it
automatically:

| Call | Total | `load_duration` | Generation |
|---|---|---|---|
| Cold, model not loaded | 5,063 ms | 4,852 ms | 206 ms |
| Warm | 53 ms | 2 ms | 48 ms |

A model that isn't installed returns HTTP 404 with `model '<name>' not found`. When Ollama isn't
running, the connection is refused.

The conclusion is that a citation check proves a cited passage was retrieved, not that it supports
the answer. Full IDs only caught invented answers because the model mangled them, which broke good
answers too.

## Goals / Non-Goals

**Goals:**
- A working answer with checked citations, completing step 1.
- Outcomes that the golden set at step 2 can score: answered, not found, and each kind of failure.
- Tests that run offline in CI.

**Non-Goals:**
- Proving that an answer is supported by its citations. Step 2 measures this with out-of-corpus
  questions, and comparing a larger model is planned.
- Preferring current RFCs over obsolete ones, which belongs to step 3.
- Streaming, conversation history or an HTTP API. The HTTP API is step 4.

## Decisions

- **One new module, `answer_generator.py`**: It builds the prompt, calls Ollama, and parses and checks
  the model's output. `query.py` keeps the public API and orchestrates retrieval, generation and the
  response. This keeps the model call behind a single private function, `_post_chat`, that tests can
  replace, and it matches the design note in `add-query-interface` about a private answer function.

- **Call Ollama's HTTP API with `requests`**: It's one `POST /api/chat`. That keeps the hand-built
  approach visible and adds no dependency. The `ollama` package was rejected as a convenience the
  project doesn't need.

- **Structured output with a JSON schema**: The request sets Ollama's `format` to a schema with
  `found` (boolean), `answer` (string) and `citations` (an array of strings). The spike showed it
  produces valid JSON reliably. Inline citation markers in free text were rejected, because they'd
  need parsing, and step 2 can score claims separately if that becomes useful.

- **Short labels, mapped in code**: Passages are labeled `P1` to `Pn`, with the RFC number, section
  number and title shown beside each label. Code maps cited labels back to chunk IDs. The spike showed
  this is the only format where good answers cite correctly. The cost is that invented answers can
  cite real labels, which is recorded as a risk below rather than hidden. Full IDs were rejected
  because they broke good answers, and a constrained `enum` of valid labels was rejected because it
  would force a citation even when the model has none.

- **Citation rules**: Keep only labels that were sent, de-duplicate in the order first cited, and
  treat an answer with no valid citations as not found, discarding its text. Matching is exact, apart
  from surrounding whitespace, so that the check stays meaningful.

- **Not found is a success**: The response has `success` true, `found` false, the message "The indexed
  RFCs don't answer this question.", and no citations. The system worked correctly, and step 2 can
  score it separately from failures. There are three paths to not found: no search results, which
  skips the model call entirely; the model reporting `found` false; and no valid citations.

- **Response shape**:

  ```
  QueryResponse
    success: bool
    answer: Optional[str]
    found: Optional[bool]          None on failure
    citations: list[Citation]      empty unless found
    timings: Optional[Timings]     None only when validation fails first
    error_string: Optional[str]
    error_code: Optional[QueryErrorCode]

  Citation: chunk_id, rfc_number, rfc_title, section_number, section_title
  ```

  New fields have defaults, so the existing construction calls keep working.

- **Error codes stay consecutive until the first release**: `INVALID_QUERY` stays 1. `NOT_IMPLEMENTED`
  is removed, and the new codes are `INDEX_UNAVAILABLE` 2, `MODEL_UNAVAILABLE` 3,
  `MODEL_INVALID_RESPONSE` 4 and `CONFIG_INVALID` 5. There hasn't been a release, so no outside
  caller depends on the old value, and reusing 2 keeps the numbering simple. Retiring 2 was
  considered and rejected for that reason. After the first release, a removed value is retired and
  not reused, so that an old value can't be mistaken for a new meaning.

- **`query_config.json`**:

  ```json
  {
    "index_path": "data/index.db",
    "retrieval": { "limit": 5 },
    "llm": {
      "model": "llama3.2",
      "base_url": "http://localhost:11434",
      "num_ctx": 8192,
      "max_answer_tokens": 512,
      "timeout_seconds": 120
    }
  }
  ```

  It mirrors `ingest_config.json`, with retrieval and model settings in a reviewed file. A relative
  `index_path` is resolved from the repository root. Step 5 can add an environment variable override
  for the Ollama address when it runs in Docker.

- **The prompt budget is checked before the call**: `limit` x `target_chunk_tokens` from the index
  metadata, plus 512 tokens for instructions and question, plus `max_answer_tokens`, must fit
  `num_ctx`. With today's values that's 5 x 1,100 + 512 + 512 = 6,524 of 8,192. This is the prompt
  budget that `add-rfc-ingestion` assigned to this change. Reading `target_chunk_tokens` from the
  index means a rebuilt index with larger chunks is caught here.

- **Detect a prompt Ollama cut short**: Ollama shortens an over-long prompt without an error. So if
  the response's `prompt_eval_count` reaches `num_ctx`, the query fails with
  `MODEL_INVALID_RESPONSE`, instead of answering from a partial prompt. The budget check should
  prevent this, so this catches a wrong estimate.

- **Timings on every response**:

  ```
  Timings
    total_ms          whole query
    retrieval_ms      keyword search
    model_load_ms     Ollama's load_duration; None when the model isn't called
    generation_ms     Ollama's prompt_eval_duration plus eval_duration
    prompt_tokens     Ollama's prompt_eval_count
    answer_tokens     Ollama's eval_count
    cold_start        True when model_load_ms >= 500
  ```

  Ollama's own durations are used for the model stages, and wall-clock time for the rest. Step 7
  observability can then report warm and cold latency separately, or leave cold starts out, and
  step 2 gets token counts at no cost. The 500 ms threshold sits far from both measurements: about
  2 ms warm and 4,852 ms cold. Failures that reach retrieval still report timings, because a slow
  timeout is worth measuring too. Validation failures happen before any work, so they don't.

- **Rely on Ollama to load the model**: An installed model that isn't loaded is loaded by the request
  itself, so the service doesn't run `ollama run` or check first. A preliminary `/api/ps` call was
  rejected because the request already reports the load time, and a check would add a call to every
  query.

- **No side effects when the model is unavailable**: A missing model fails with a hint to run
  `ollama pull <model>`, and a refused connection fails with a hint to start Ollama. Downloading
  about 2 GB, or starting a server, aren't things a query should do, and at step 5 the model will be
  a separate service anyway.

- **Leave `keep_alive` at Ollama's default**: Setting it longer would make cold starts rarer. It's left
  out because the `cold_start` flag already keeps cold starts out of performance figures, and one
  fewer setting keeps the configuration focused. It can be added later if cold starts become a
  problem for users.

- **Model settings**: `temperature` 0 for repeatable answers, `num_ctx` from config, and
  `num_predict` set to `max_answer_tokens`. `stream` is false.

- **Prompt**: A system message sets the rules: use only the passages, set `found` false when they
  don't answer, otherwise answer briefly, and cite the label of every passage used. The user message
  holds the labeled passages and then the question. The wording is in `answer_generator.py`, so that
  step 2 can measure changes to it.

- **Failure mapping**:

  | Condition | Error code |
  |---|---|
  | Invalid configuration, or a budget that doesn't fit | `CONFIG_INVALID` |
  | Index missing or unreadable, including its metadata | `INDEX_UNAVAILABLE` |
  | Connection refused, timeout, or an HTTP error from Ollama, including a missing model | `MODEL_UNAVAILABLE` |
  | Output that isn't JSON in the expected shape, or a prompt cut short | `MODEL_INVALID_RESPONSE` |

- **Tests stay offline**: Unit tests replace `_post_chat` with canned responses, and use a small index
  built from fixture chunks. One integration test calls the real model, and it runs only when
  `OLLAMA_TESTS=1` is set, following the existing network test's pattern.

## Risks / Trade-offs

- [`llama3.2` invents answers to out-of-corpus questions and cites real passages] → Recorded in the
  proposal and README rather than hidden. Step 2's golden set includes out-of-corpus questions to
  measure it, and a larger model is planned for comparison.
- [Keyword search returns obsolete RFCs first, such as RFC 5077 for TLS 1.3 resumption] → This is the
  conflict step 3 addresses. Citations show the RFC number, so a reader can see it.
- [Answers vary between model versions] → The model name is in the configuration, and step 2 measures
  answers rather than this change asserting exact wording.
- [The first query is slow while the model loads] → Accepted, and reported through `cold_start` and
  `model_load_ms`, with a note on the console. The timeout is 120 seconds, against measured loads of
  about 5 to 6.4 seconds.
- [The 512-token allowance for instructions is an estimate] → The `prompt_eval_count` check catches it
  if it's wrong, and the measured prompts were 1,000 to 1,850 tokens in total.

## Results

The implementation was run against the real index and `llama3.2` with the spike's 10 questions:

| Question | Outcome | Citations | Total time |
|---|---|---|---|
| What does a 404 status code mean? | Answered | RFC 9110, 7231 and 2616 sections on 404 | 388 ms |
| What does the three-way handshake do? | Answered | RFC 793 and 9293 connection sections | 841 ms |
| How does a client resume a TLS 1.3 session? | Answered | RFC 5077 and 8446, both obsolete; not 9846 | 838 ms |
| When must a sender not send Content-Length? | Answered | RFC 7230, 9112 and 9110 Content-Length sections | 674 ms |
| What is the capital of France? | Not found | None | 465 ms |
| How does IPv6 neighbor discovery work? | Not found | None | 399 ms |
| How do DNS zone transfers work? | Invented answer | Unrelated passages | 644 ms |
| How does BGP select a best path? | Invented answer | Unrelated passages | 966 ms |
| What port does SMTP use? | Invented answer | Unrelated passages | 563 ms |
| What is a stateless reset in QUIC? | Invented answer | Unrelated passage | 780 ms |

In-corpus questions were answered with relevant citations. Two of six out-of-corpus questions were
reported as not found, and four were answered from the model's own knowledge while citing real
passages, as the spike predicted. The TLS 1.3 answer is a clear case for step 3, because it cited
only obsolete RFCs.

After unloading the model, the next query reported a 5.0 second load as a cold start, and the one
after it reported a 2 ms load. A model that isn't installed, and an address with nothing listening,
each failed with the matching setup hint and exit status 1.

## Migration Plan

`query()` keeps its signature. Callers that checked for `NOT_IMPLEMENTED` should handle `found` and
`citations` instead, which affects only this repository's tests. To roll back, revert the pull
request.
