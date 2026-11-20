# Proposal

## Why

The three commands find generated data in three different ways:

- `rfc-ingest` writes RFCs and the index under `--data-dir`, which defaults to `data/`.
- `rfc-query` reads the index from `index_path` in `query.json`.
- `rfc-search` reads `--index`, which defaults to `data/index.db`.

If the index is built in another directory, `rfc-query` doesn't find it until `query.json` is edited
as well. The roadmap's Docker and cloud steps need to put data on a mounted volume, choosing it the
same way the configuration directory is chosen now: without editing version-controlled files.

## What Changes

- The data directory can be selected. The order of precedence is:
  1. a `--data-dir` flag on `rfc-ingest`, `rfc-query` and `rfc-search`,
  2. the `RFC_QA_DATA_DIR` environment variable,
  3. `data/` at the repository root.
  A relative directory resolves from the working directory, and an empty variable counts as unset.
- The index is always `index.db` in the data directory, and downloaded RFCs are in its `rfcs/`
  folder. Every command finds the index the same way, so building and querying can't disagree.
- `index_path` is removed from the query configuration. The project isn't deployed anywhere yet, so
  no other copies of the configuration need it. There's no check for a leftover key, which is ignored
  like any other unknown key.
- `rfc-search` keeps `--index` for pointing at one index file. It takes precedence over the data
  directory.
- `rfc-ingest` creates the data directory if it doesn't exist, as it does now. For `rfc-query` and
  `rfc-search`, a missing data directory is a missing index, reported by the existing index error that
  names the path and says to run `rfc-ingest`.
- The programmatic API gains an optional keyword argument for the data directory, with the same
  precedence. Callers that pass only the question, or the configuration directory, see no change.

Out of scope: separate locations for the RFCs and the index, other index file names, and moving the
existing `data/` directory.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `project-packaging`: Data resolves from a selectable data directory, which defaults to `data/` at
  the repository root. The rule for relative `index_path` values is replaced, and `rfc-search` keeps a
  single-file index override.
- `answer-generation`: The index path is no longer part of the query configuration.

## Impact

- Code: `rfc_qa/paths.py` (the default data directory, and how a data directory is chosen),
  `rfc_qa/ingestion/ingest.py`, `rfc_qa/query.py` and `rfc_qa/retrieval/keyword_index.py` (the
  `--data-dir` flag, the environment variable and the API argument).
- Configuration: `config/query.json` loses `index_path`.
- Tests: `tests/test_query.py` selects its fixture index through the data directory instead of
  `index_path`. `tests/test_paths.py`, `tests/ingestion/test_ingest.py` and
  `tests/retrieval/test_keyword_index.py` gain data-directory tests. `tests/conftest.py` also clears
  `RFC_QA_DATA_DIR`.
- Docs: `README.md`. `ARCHITECTURE.md` waits for the next release, as before.
- No new dependencies. CI is unaffected.
