# answer-generation Specification

## Purpose

Produces an answer to an RFC question from passages retrieved from the index, with citations to
the RFC sections used, and reports clearly when the indexed RFCs don't answer the question.

## Requirements

### Requirement: Retrieve passages for a question

The service SHALL search the keyword index with the question and pass the top results, up to the
configured retrieval limit, to the model. When the search returns no passages, the service SHALL
report the question as not found without calling the model.

#### Scenario: Passages retrieved

- **WHEN** a question matches chunks in the index
- **THEN** up to the configured limit of the best-ranked chunks are sent to the model

#### Scenario: No passages retrieved

- **WHEN** a question matches nothing in the index
- **THEN** the response is not found, and the model is not called

### Requirement: Answer only from the retrieved passages

The service SHALL instruct the model to answer using only the retrieved passages, and to report
whether they answer the question. The model's output SHALL be structured, giving whether an answer
was found, the answer text, and the passages used.

#### Scenario: Passages answer the question

- **WHEN** the retrieved passages answer the question
- **THEN** the response is found, with the model's answer

#### Scenario: Model reports no answer

- **WHEN** the model reports that the passages don't answer the question
- **THEN** the response is not found

### Requirement: Check citations against the retrieved passages

Passages SHALL be labeled for the model with short labels, and the service SHALL map each cited
label back to its chunk. A citation SHALL be kept only when it names a passage that was sent to the
model. Repeated citations SHALL be kept once, in the order first cited.

#### Scenario: Valid citations

- **WHEN** the model cites `P1` and `P3`
- **THEN** the response cites the first and third retrieved chunks

#### Scenario: Invented citation

- **WHEN** the model cites a label that wasn't sent, such as `P9` or `RFC4271`
- **THEN** that citation is dropped

#### Scenario: Repeated citation

- **WHEN** the model cites `P2` twice
- **THEN** the chunk appears once in the citations

#### Scenario: No valid citations

- **WHEN** the model reports an answer but none of its citations are valid
- **THEN** the response is not found, and the model's answer is not returned

### Requirement: Report not found as a successful outcome

When the indexed RFCs don't answer a question, the service SHALL return a successful response
marked not found, with a standard message saying so and no citations.

#### Scenario: Out-of-corpus question

- **WHEN** a question is about something the indexed RFCs don't cover and the model reports no answer
- **THEN** the response has `success` true, `found` false, the standard not-found message, and no citations

### Requirement: Describe each citation

Each citation SHALL give its chunk ID, RFC number and title, and section number and title, so that a
reader can find the cited text.

#### Scenario: Citation fields

- **WHEN** an answer cites a chunk
- **THEN** the citation provides the chunk ID, RFC number, RFC title, section number and section title from the index

### Requirement: Configure the model and retrieval

The service SHALL read the model name, Ollama address, context window size, request timeout, answer
length limit, retrieval limit and index path from a version-controlled configuration. It SHALL fail
before calling the model when a value is missing or invalid.

#### Scenario: Different model

- **WHEN** the configuration names another installed model
- **THEN** answers come from that model with no code change

#### Scenario: Invalid configuration

- **WHEN** a configuration value is missing, has the wrong type, or is not positive where it must be
- **THEN** the response is a failure with the configuration error code, naming the value

### Requirement: Keep the prompt within the context window

The service SHALL check, before calling the model, that the retrieval limit times the index's chunk
token target, plus the prompt and answer allowances, fits the configured context window. It SHALL
treat a response whose reported prompt size reaches the context window as cut short.

#### Scenario: Budget too large

- **WHEN** the retrieval limit and the index's chunk token target can't fit in the context window
- **THEN** the response is a failure with the configuration error code, and the model is not called

#### Scenario: Prompt cut short

- **WHEN** the model reports a prompt size equal to or above the context window
- **THEN** the response is a failure with the invalid model response error code

### Requirement: Report model and index failures

The service SHALL return a failure response, rather than raising, when the index can't be read, the
model can't be reached or returns an error, the request times out, or the model's output isn't valid
structured output.

#### Scenario: Index missing

- **WHEN** the configured index doesn't exist
- **THEN** the response is a failure with the index unavailable error code

#### Scenario: Ollama not running

- **WHEN** the model service can't be reached or the request times out
- **THEN** the response is a failure with the model unavailable error code, describing the problem and saying to start Ollama

#### Scenario: Model not installed

- **WHEN** the configured model isn't available in Ollama
- **THEN** the response is a failure with the model unavailable error code, naming the model and saying to run `ollama pull` for it

#### Scenario: No side effects on the model service

- **WHEN** the model isn't installed or Ollama isn't running
- **THEN** the service doesn't download the model or start Ollama

#### Scenario: Unreadable model output

- **WHEN** the model's output isn't valid JSON in the expected shape
- **THEN** the response is a failure with the invalid model response error code

### Requirement: Report timings and cold starts

Every response that reaches the retrieval stage SHALL report its total time and retrieval time in
milliseconds. When the model is called, it SHALL also report the model load time, the generation
time, and the prompt and answer token counts, taken from the model service. It SHALL mark a cold
start when the model load time is 500 milliseconds or more.

#### Scenario: Warm model

- **WHEN** the model is already loaded and answers the question
- **THEN** the timings report a model load time below 500 milliseconds and no cold start

#### Scenario: Model loaded for this query

- **WHEN** the model service has to load the model before answering
- **THEN** the query still answers, and the timings report the load time and mark a cold start

#### Scenario: No model call

- **WHEN** nothing is retrieved, so the model isn't called
- **THEN** the timings report total and retrieval time, with no model load time, generation time or token counts, and no cold start

#### Scenario: Model failure

- **WHEN** the model call fails
- **THEN** the failure response still reports total and retrieval time
