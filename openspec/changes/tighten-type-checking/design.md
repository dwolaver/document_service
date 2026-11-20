# Design

## Context

`pyproject.toml` configures mypy 2.4.1 with `files = ["rfc_qa", "scripts", "tests"]`,
`explicit_package_bases` and `warn_unused_configs`, at default strictness. The pre-commit hook and
CI's `quality` job both run `mypy` with that configuration.

Measured on `main`:

| | `--strict` findings | mostly |
|---|---|---|
| `rfc_qa/` (13 files, about 100 functions) | 227 | missing annotations, and calls to unannotated functions |
| `scripts/` (1 file) | 36 | the same |
| `tests/` (11 files, 255 test functions) | 1,004 | the same |

With strict code and relaxed tests, the tests leave 5 findings. Each is a test patching a name that a
module imported, such as `monkeypatch.setattr(rfc_downloader.requests, "get", ...)`, which
`--strict`'s `no_implicit_reexport` rejects. Setting `implicit_reexport` for the tests doesn't help,
because the setting applies to the module being imported from.

The findings that aren't about missing annotations are in code that reads data from outside:

- `ingest.py`: `_parse_corpus_entry` checks `_is_integer(number)` and then compares `number <= 0`.
  mypy can't see that the helper narrowed `number` from `Any | None`.
- `answer_generator.py`: `_parse_answer` passes `content`, which may be `None`, to `json.loads`. The
  resulting `TypeError` is caught and reported as a model error.
- `chunker.py`: two empty containers need element types.

JSON enters the code in four places: `load_query_config`, `ingest._load_json`, `_parse_answer` and
`scripts/update_architecture.py`.

## Goals / Non-Goals

**Goals:**
- `mypy --strict` passes for `rfc_qa/` and `scripts/`, and test bodies are checked.
- `Any` from parsed JSON is narrowed where the code already validates it, so annotated functions
  receive real types.
- Behavior is unchanged, apart from the bug fix below: the same messages, error codes and outputs,
  and the same results for the existing tests.

**Non-Goals:**
- Annotating tests and fixtures.
- Modeling the JSON shapes with `TypedDict`. The loaders already validate each field and build
  dataclasses, so the dataclasses are the typed form.

## Decisions

### Configuration

```toml
[tool.mypy]
files = ["rfc_qa", "scripts", "tests"]
explicit_package_bases = true
warn_unused_configs = true
strict = true
enable_error_code = ["ignore-without-code"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_incomplete_defs = false
disallow_untyped_calls = false
disallow_untyped_decorators = false
check_untyped_defs = true
```

`strict` includes `warn_unused_ignores`, so an unneeded suppression fails. `ignore-without-code`
makes a bare `# type: ignore` fail too. The override turns off only the annotation requirements for
tests. Everything else in `strict` still applies to them, and `check_untyped_defs` checks the bodies of
their unannotated functions.

Alternative: separate strict and relaxed mypy runs. Rejected because one configuration, with one
override, is what the hook and CI already run.

### Narrowing instead of casting

Parsed JSON is typed `Any` at the call to `json.load` or `json.loads`, and nowhere else. Code after a
check narrows it:

- `_is_integer` becomes a `TypeGuard[int]`, so `number` is an `int` after the check. The same applies
  to the query configuration helpers, which return the validated value with its type
  (`_positive_integer(...) -> int`, `_non_empty_string(...) -> str`).
- `_parse_answer` checks `isinstance(content, str)` before `json.loads`. The `None` case raises the
  same `ModelResponseError` message as before.
- `_call_model` checks that Ollama's JSON body is an object, and raises
  `ModelResponseError("Ollama returned a response that isn't a JSON object.")` otherwise. Before this
  change, `generate_answer` called `payload.get(...)` on the body before any check, so a JSON list or
  string crashed with `AttributeError` all the way out of `query()`. Two more spots had the same
  problem: `_ollama_error` called `.get("error")` on a non-200 response body that might not be an
  object, and a non-integer `load_duration` reached the millisecond conversion. The error body now
  falls back to an empty message, and `load_duration` is treated as missing when it isn't an integer,
  as every other count and duration already is. Ollama always sends objects and integers there, so
  only malformed responses are affected. This is the one behavior change: unusable model output fails
  as the answer-generation spec requires, instead of crashing. The repository owner approved it when
  typing found it, and tests cover each case.
- Dictionaries read from JSON are annotated `dict[str, Any]` after an `isinstance(..., dict)` check,
  and each field is checked before use, as the code does today.

`cast` and `# type: ignore[code]` are used only where narrowing isn't possible, each with a comment
giving the reason. None are expected.

Alternative: `Any` throughout the loaders. Rejected by the repository owner, because it would let the
types the dataclasses promise go unchecked.

### Annotations follow the code as it is

Annotations describe the current behavior. Where code has to change for mypy, such as a narrowing
check, the change keeps the same outcome for every input. Built-in generics (`list[str]`,
`str | None`) replace `typing.List` and `Optional`, which Python 3.14 doesn't need. ruff's selected
rules don't include pyupgrade, so this is done by hand only in lines that are annotated anyway.

### Tests narrow optional values

Once the package is annotated, the checked test bodies see its real types. About 46 lines read a value
typed `X | None` without a check, such as `"404" in response.error_string` or
`response.timings.total_ms`. The tests narrow these explicitly, usually with
`assert value is not None` before the line that reads it, so `None` checking stays on in tests as in
the package.

Two tests deliberately pass a wrong type to check runtime validation: `query(None)` and friends, and
`download_rfc("1")` and friends. Each of those calls gets a `# type: ignore[arg-type]` with a comment
saying the wrong type is the point of the test.

Alternative: `strict_optional = false` for the tests. Rejected by the repository owner, to keep
`None` checking the same in tests and in the code.

### The tests patch the real module

The five tests patch `requests.get`, `os.replace` and `subprocess.run` on the modules themselves,
imported in the test. `rfc_downloader.requests` and `requests` are the same module object, so the
patch is the same patch. pytest's `monkeypatch` undoes it after the test, as before.

Alternative: string targets, such as `monkeypatch.setattr("rfc_qa.ingestion.rfc_downloader.requests.get", ...)`.
Rejected because mypy can't check a string.

### Order of work

Annotate leaf modules first (`paths`, `chunk`, `rfc_parser`, `chunker`, `keyword_index`,
`rfc_downloader`, `answer_generator`), then the modules that call them (`ingest`, `query`), then the
script. Calls into an unannotated function are errors under `strict`. Working upward means each module
is checked against annotated dependencies. The strict configuration is turned on last, once all
modules pass with `mypy --strict` run directly on them.

## Risks / Trade-offs

- [A narrowing change alters behavior for some odd input] → Every change keeps the existing message
  and outcome, and the test suite covers the validators' error paths. The suite must give the same
  result after each module.
- [Large diff] → Mostly signatures. It's split by group, so each commit is reviewable on its own.
- [Tests stay unannotated] → Their bodies are checked, which is where type errors in tests would be.
  Annotating them can follow later if wanted.

## Migration Plan

All in one pull request. Nothing changes for developers beyond writing annotations in new code. To
roll back, revert the commit. The checks then return to default strictness.
