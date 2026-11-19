# Design

## Context

`tests/` holds nine test modules and a `fixtures/` folder, with no `__init__.py` and no
`conftest.py`. pytest runs in its default `prepend` import mode, which imports each test module by
its file name alone. That works only while every test file name is unique. `pytest.ini` sets
`pythonpath = .`, so the release-script tests can import `scripts.update_architecture`.

Two tests use their own location:

- `test_rfc_parser.py` and `test_ingest.py` find the fixtures with `dirname(__file__)/fixtures`.
- `test_ingest.py` also works out the repository root as two `dirname` calls above itself. That
  would point at `tests/` once the file is one folder deeper.

No test module imports another.

## Goals / Non-Goals

**Goals:**
- Each test module's folder matches the folder of the code it tests.
- The layout allows the same file name in different folders.
- The test count and results are unchanged: 321 passed, 2 skipped.
- `git log --follow` keeps working for every moved test.

**Non-Goals:**
- One test file per module. `rfc_qa/chunk.py` and `rfc_qa/paths.py` stay covered through their
  callers.
- Shared fixtures in `conftest.py`. Each folder's tests keep their own helpers, as they do today.

## Decisions

### Layout

```
tests/
  test_query.py                 rfc_qa/query.py
  test_packaging.py             the package as a whole (commands, root modules, subpackages)
  ingestion/
    fixtures/                   used only by the parser and ingest tests
    test_rfc_downloader.py
    test_rfc_parser.py
    test_chunker.py
    test_ingest.py
  retrieval/
    test_keyword_index.py
  generation/
    test_answer_generator.py
  scripts/
    test_update_architecture.py scripts/update_architecture.py
```

- **`test_packaging.py` stays at the top.** It checks the package as a whole, so it matches
  `rfc_qa/` itself rather than any one module.
- **The release-script tests go in `tests/scripts/`.** That mirrors the repository's `scripts/`
  folder, so every test file's place follows one rule: its path under `tests/` matches the code's
  path under `rfc_qa/`, or under the repository root for `scripts/`.
- **The fixtures move with the ingestion tests.** They're RFC excerpts used only by the parser and
  ingest tests. Keeping them next to those tests means `dirname(__file__)/fixtures` keeps working
  without any change.

### Import mode: `importlib`, not `__init__.py` files

`pytest.ini` gains `addopts = --import-mode=importlib`. In this mode pytest imports each test file
under a name derived from its path, so `tests/ingestion/test_x.py` and `tests/retrieval/test_x.py`
can both exist. pytest's documentation recommends it for new projects. I ran the current suite with
`--import-mode=importlib` and got 321 passed, 2 skipped.

Its known limit is that test modules can't import one another. None does today, and shared helpers
would go in a `conftest.py`, which works in this mode.

Alternative: an `__init__.py` in `tests/` and in each subfolder, staying in `prepend` mode. This also
allows repeated file names, but it makes `tests` an importable package that sits next to `rfc_qa`
and `scripts` on the path. It also adds five files whose only job is to configure pytest. Rejected
in favor of one line of configuration.

`pythonpath = .` stays, because the release-script tests still import `scripts.update_architecture`
from the repository root.

### Repository root from `rfc_qa.paths`

`test_ingest.py` replaces its own `ROOT` calculation with `rfc_qa.paths.REPO_ROOT`, as
`test_query.py` already does. The tests then don't depend on how deep they sit.

### Moves with `git mv`

Each file moves with `git mv`, and only `test_ingest.py` changes content. That keeps every move
detectable as a rename, so `git log --follow` keeps the history.

## Risks / Trade-offs

- [Under `importlib` mode, `tests/scripts/` could shadow the real `scripts` package] → pytest
  registers test modules under path-derived names such as `tests.scripts.test_update_architecture`,
  not `scripts`. The release-script tests import `scripts.update_architecture`, so if it were
  shadowed they would fail at collection. The full run in the tasks would catch it.
- [Stale `__pycache__` folders from the old layout] → They're ignored by git and don't affect
  collection in `importlib` mode. The tasks clear `tests/__pycache__` anyway.
- [A test silently stops being collected after the move] → The tasks compare the collected test
  IDs, by test name, before and after the move. The total must stay at 323.
- [Someone runs one moved file by its old path] → It fails with "file not found", which makes the
  new path obvious. No compatibility shim is needed.

## Migration Plan

All in one pull request. After it merges, developers run tests by the new paths, for example
`pytest tests/ingestion`. To roll back, revert the commit. Nothing outside the tests changes.
