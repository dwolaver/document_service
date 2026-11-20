# Tasks

## 1. Annotate the package

- [x] 1.1 Annotate the leaf modules `rfc_qa/paths.py`, `rfc_qa/chunk.py`, `rfc_qa/ingestion/rfc_parser.py`, `rfc_qa/ingestion/chunker.py`, `rfc_qa/retrieval/keyword_index.py` and `rfc_qa/ingestion/rfc_downloader.py`, using built-in generics; verify `mypy --strict` on those files reports nothing, and `pytest` gives the same pass and skip counts as on `main`
- [x] 1.2 Annotate `rfc_qa/generation/answer_generator.py`, replacing `typing.List` and `Optional`, and narrow the model output in `_parse_answer` with an `isinstance(content, str)` check that raises the same `ModelResponseError` message as before, and make `_call_model` reject a JSON body that isn't an object with a `ModelResponseError` (the bug fix in design.md); verify `mypy --strict` on the file reports nothing, a new test shows a JSON list body gives `ModelResponseError` from `generate_answer` and `MODEL_INVALID_RESPONSE` from `query()`, and the existing tests give the same results, including the invalid-output tests
- [x] 1.3 Annotate `rfc_qa/ingestion/ingest.py`, making `_is_integer` a `TypeGuard[int]` and typing the validated loader results; verify `mypy --strict` on the file reports nothing, and `pytest` gives the same counts, including every manifest and configuration validation test
- [x] 1.4 Annotate `rfc_qa/query.py`, replacing `typing.List` and `Optional` and making the configuration helpers return their validated types; verify `mypy --strict rfc_qa` reports nothing, and `pytest` gives the same counts

## 2. Annotate the release script

- [x] 2.1 Annotate `scripts/update_architecture.py`, narrowing any parsed JSON as in design.md; verify `mypy --strict scripts` reports nothing, and `pytest tests/scripts` gives the same counts

## 3. Strict configuration

- [x] 3.1 Change the five tests that patch an imported name (`ua.subprocess`, `rfc_downloader.requests` three times, `rfc_downloader.os`) to patch the module itself, imported in the test; verify each test still passes, and fails if the patched function is replaced with one that raises (checked once, then reverted)
- [x] 3.2 Set `strict = true`, `enable_error_code = ["ignore-without-code"]` and the `tests.*` override from design.md in `pyproject.toml`, and fix what the checked test bodies then report: narrow optional values with explicit checks, and give the two deliberate wrong-type calls a `# type: ignore[arg-type]` with its reason (see "Tests narrow optional values" in design.md); verify `pre-commit run --all-files` passes, and, in a scratch copy, that each scenario of the modified requirement behaves as specified: an unannotated function in `rfc_qa` fails, a partly annotated one fails, an unannotated test passes while a wrong method call in its body fails, a bare `# type: ignore` fails, and an unneeded `# type: ignore[code]` fails
- [x] 3.3 Update the README's "Development" section, which says mypy checks only annotated functions: say the package and scripts are checked strictly and must be annotated, and the tests' bodies are checked; verify the README matches `pyproject.toml`
- [x] 3.4 Confirm no behavior changed apart from the bug fix: `pytest` passes every test that passes on `main`, plus the new bug-fix tests, with the same skips, `grep -rn "type: ignore\|cast(" rfc_qa scripts` finds nothing, or only lines whose comment gives the reason, and `rfc-ingest --help`, `rfc-query --help` and `rfc-search --help` print the same text as on `main`

## Workflow follow-up

- Open a pull request from `tighten-type-checking`. The `test`, `quality` and `secrets` checks must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and the checks must pass again.
- Archive the change on this branch as the last step, which syncs the code-quality spec, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
