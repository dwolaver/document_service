# Tasks

## 1. Configuration and response shape

- [x] 1.1 Add `query_config.json` with the values from design.md, and loading in `query.py` that validates each value and resolves a relative `index_path` from the repository root; verify unit tests cover a valid file and missing, wrong-type and non-positive values
- [x] 1.2 Add `Citation`, `Timings`, the `found`, `citations` and `timings` fields on `QueryResponse`, and the new error codes, removing `NOT_IMPLEMENTED` and numbering the codes consecutively from 2, since there hasn't been a release; verify unit tests check field defaults and each code's integer value

## 2. Answer generation

- [x] 2.1 Implement prompt building in `answer_generator.py`, labeling passages `P1` to `Pn` with their RFC number, section number and title; verify unit tests show the labels, the passage text and the question in the prompt, in order
- [x] 2.2 Implement the Ollama call through a private `_post_chat`, with the JSON schema, `temperature` 0, `num_ctx`, `num_predict` and the timeout; verify unit tests with a replaced `_post_chat` check the request body, and that connection errors, timeouts and HTTP errors, including a missing model, map to `MODEL_UNAVAILABLE`, with a hint to start Ollama or run `ollama pull <model>`; verify too that nothing tries to pull a model or start Ollama
- [x] 2.3 Implement output parsing and citation checks: keep sent labels only, de-duplicate in order, treat no valid citations as not found, and reject invalid JSON, the wrong shape, or a `prompt_eval_count` that reaches `num_ctx`; verify unit tests cover each scenario in the answer-generation spec

## 3. Query pipeline

- [x] 3.1 Replace the `NOT_IMPLEMENTED` branch in `query()` with retrieval, the budget check, generation and response building, including not found without a model call when nothing is retrieved; verify unit tests with a fixture index and a replaced `_post_chat` cover answered, all three not-found paths, a missing index, an over-budget configuration, and every model failure
- [x] 3.2 Build `Timings` from wall-clock time and Ollama's reported durations and counts, with `cold_start` when `model_load_ms` is 500 or more; verify unit tests with canned Ollama responses cover a warm call, a cold call, no model call, and a model failure
- [x] 3.3 Update the console wrapper to print citations after the answer, to print a cold-start note with the load time, and to print the not-found message with exit status 0; verify unit tests check standard output, standard error and exit codes for answered, cold-start, not-found and failed queries
- [x] 3.4 Update `tests/test_query.py` for the removed `NOT_IMPLEMENTED` behavior; verify the full suite passes offline

## 4. Real model verification

- [x] 4.1 Add an integration test that answers one corpus question through the real model, run only when `OLLAMA_TESTS=1` is set, and register its marker in `pytest.ini`; verify it passes locally with Ollama running, and is skipped without the variable
- [x] 4.2 Run the 10 spike questions through `python query.py` with the real index and model; verify each in-corpus answer cites relevant RFC sections, record which out-of-corpus questions return not found, and record response times
- [x] 4.3 Unload the model with a `keep_alive` of 0, then ask two questions; verify the first reports `cold_start` with a load time of several seconds and prints the console note, and the second is warm
- [x] 4.4 Stop Ollama, or point the configuration at a model that isn't installed, and run a query; verify the console prints a model unavailable error with the matching setup hint and exits non-zero

## 5. Documentation

- [x] 5.1 Update the README: show how to ask a question, note that Ollama and the index are required, describe `query_config.json`, mark step 1 complete, update the current status, and record the invented-answer risk from design.md; verify the documented commands run as written

## Workflow follow-up

- Open a pull request from `add-answer-generation`. The `test` check must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code. Any changes are made on this branch, in the active change, and `test` must pass again.
- Archive the change on this branch as the last step, which makes the change complete and turns `archive-check` green.
- The repository owner squash merges once both checks pass, so that the code, spec and archive land as one commit on `main`.
- Remind the owner that `add-architecture-generator` is parked and ready to resume.
