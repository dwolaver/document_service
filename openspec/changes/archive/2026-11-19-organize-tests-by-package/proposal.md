# Proposal

## Why

The service code now lives in `rfc_qa`, with a subpackage for each stage, but its tests are still
nine flat files in `tests/`. Nothing in that folder shows which stage a test covers, and the
fixtures look shared even though only the ingestion tests use them. If `tests/` mirrors the package,
the tests for a module sit where you'd expect, and new stage tests (the planned retrieval backends,
for example) have an obvious place to go.

## What Changes

- Test modules move into folders that mirror `rfc_qa`:
  - `tests/ingestion/`: `test_rfc_downloader.py`, `test_rfc_parser.py`, `test_chunker.py`,
    `test_ingest.py`, and the `fixtures/` folder, which only these tests use.
  - `tests/retrieval/`: `test_keyword_index.py`.
  - `tests/generation/`: `test_answer_generator.py`.
  - `tests/`: `test_query.py`, matching `rfc_qa/query.py`, and `test_packaging.py`, which checks
    the package as a whole.
  - `tests/scripts/`: `test_update_architecture.py`, matching `scripts/` at the repository root.
- pytest imports test modules in a way that allows the same file name in two folders, so the layout
  can grow without name clashes.
- Tests that work out the repository root from their own location use `rfc_qa.paths.REPO_ROOT`
  instead, so moving a test can't break it.
- The README's license section points to the fixtures' new location.

No test is added, removed or changed in what it checks. The test count stays at 321 passed and 2
skipped.

Out of scope: splitting or merging test modules, adding tests for modules that have none
(`rfc_qa/chunk.py` and `rfc_qa/paths.py` are covered through their callers), and shared conftest
fixtures.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
<!-- None. Only the test layout changes, so the change sets skip_specs: true. -->

## Impact

- Moved: every test module, and `tests/fixtures/`.
- Updated: `pytest.ini` (import mode), `tests/ingestion/test_ingest.py` (repository root), and
  `README.md` (fixtures path).
- CI keeps running bare `pytest` and finds tests in the new folders without any change.
- `ARCHITECTURE.md` doesn't describe test files, so nothing there goes stale.
