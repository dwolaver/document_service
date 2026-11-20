# Design

## Context

`rfc_qa/paths.py` defines `DATA_DIR` (`data/` at the root) and `INDEX_PATH` (`data/index.db`). It also
defines `resolve_config_dir`, which returns a frozen `ConfigDir(path, source)` and raises
`ConfigDirError` when the directory is missing. The data paths are used like this today:

- `rfc-ingest`: `--data-dir`, which defaults to `paths.DATA_DIR`. `run_ingestion(corpus_path,
  config_path, data_dir)` writes `rfcs/` and `index.db` under it, and creates the directories it
  needs.
- `rfc-query`: `load_query_config` validates `index_path` and joins it to `REPO_ROOT`. `_answer` reads
  `config.index_path`. `main` resolves `--config-dir` itself, so that an error names the flag, then
  calls `query(question, config_dir=path)`.
- `rfc-search`: `--index`, which defaults to `paths.INDEX_PATH` through `DEFAULT_INDEX_PATH`.
  `search()` already reports a missing index as "Index not found: ... Run rfc-ingest to build it."

`tests/test_query.py` selects its fixture index by writing `index_path` into a temporary
`query.json`, through about twenty uses of `_with(index_path=...)`.

## Goals / Non-Goals

**Goals:**
- One rule for finding the data directory, shared by all three commands and the API, built the same
  way as the configuration directory rule.
- One place, `paths`, that knows the index is `index.db` in the data directory.
- Tests that give the same result whatever `RFC_QA_DATA_DIR` is set to in the developer's shell.

**Non-Goals:**
- Checking that the data directory exists before a query or search. The index check already fails
  clearly, and naming the missing index is more useful than naming the missing directory.

## Decisions

### Resolving the data directory in `rfc_qa/paths.py`

`paths.py` gains `DEFAULT_DATA_DIR = REPO_ROOT/data`, `DATA_DIR_ENV = "RFC_QA_DATA_DIR"`,
`RFCS_FOLDER = "rfcs"`, `INDEX_FILE = "index.db"` and `resolve_data_dir(explicit=None,
explicit_source="--data-dir")`.

Both resolvers share one private helper that applies the order: `explicit`, then the variable if it's
set and not empty, then the default. Flag and variable values go through `os.path.abspath`. Only
`resolve_config_dir` then checks that the directory exists. `resolve_data_dir` doesn't, because
ingestion creates the directory, and queries and searches report the missing index instead.

`ConfigDir` is renamed to `SelectedDir(path, source)` and used by both resolvers, with `file(name)`
as before. `ConfigDirError` keeps its name.

`DATA_DIR` and `INDEX_PATH` are removed, so that nothing can find data without going through the
resolution, as `CORPUS_PATH` and the other configuration paths were removed before.

Alternative: a `DataDir` class beside `ConfigDir`. Rejected because the two would be identical.

### `index_path` leaves the query configuration

`load_query_config(path)` no longer returns an index path. `QueryConfig.index_path` is removed, and
`_answer(user_query, config, index_path)` takes the index path as an argument. `config/query.json`
drops the key.

A leftover `index_path` isn't checked for: it's ignored like any other unknown key. The project
isn't deployed anywhere yet, so the only query configuration is the one in this repository.

Alternative: reject a configuration that still sets `index_path`, naming what replaced it. Rejected
by the repository owner, because there are no other copies of the configuration to catch.

### `rfc-query` and the API

`query(user_query, *, config_dir=None, data_dir=None)` gains a keyword-only argument. It resolves
the data directory with the source label `"data_dir argument"`, and reads `INDEX_FILE` from it.
`main` adds `--data-dir`, resolves it with `resolve_data_dir(args.data_dir)` beside `--config-dir`,
and passes both paths to `query`, as it already does for the configuration directory. The
query-interface spec requires the console wrapper to invoke the programmatic entry point, so `main`
keeps calling `query`. The second resolution inside `query` is cheap, and the data directory's source
label never appears in a message.

`main` keeps catching `ConfigDirError` for the configuration directory. The data directory can't
raise.

Alternative: a private `_run` that takes both resolved directories, called by `query` and `main`.
Rejected because `main` would no longer invoke the programmatic entry point, as the query-interface
spec requires.

### `rfc-ingest`

`--data-dir` now defaults to `None`, and `main` resolves it with `resolve_data_dir(args.data_dir)`.
`run_ingestion` doesn't change, but it takes the RFC folder and index file names from `paths`.
`DEFAULT_DATA_DIR` in `ingest.py` is removed.

### `rfc-search`

`--data-dir` is added. `--index` defaults to `None`. When `--index` is given, it's used and the data
directory isn't resolved. Otherwise the index is `INDEX_FILE` in `resolve_data_dir(args.data_dir)`.
`DEFAULT_INDEX_PATH` is removed. `search()` and its missing-index message don't change.

### Tests

- `tests/conftest.py` adds `RFC_QA_DATA_DIR` to the variables it clears.
- `tests/test_paths.py` covers `resolve_data_dir`: the precedence, an empty variable, relative paths,
  and a missing directory being returned rather than raised.
- In `tests/test_query.py`, the `setup` fixture builds its index as `index.db` in a temporary data
  directory and selects it with `RFC_QA_DATA_DIR`. Tests that need another index, such as a missing
  one or one without a chunk token target, select another data directory instead of setting
  `index_path`. The tests of relative and absolute `index_path` resolution are replaced by tests of
  the data directory precedence through `data_dir` and `--data-dir`.

## Risks / Trade-offs

- [A leftover `RFC_QA_DATA_DIR` silently points queries at another index] → The missing-index message
  names the full path, and an index that exists but is the wrong one is the same risk the flag already
  has. The README documents the variable.
- [`rfc-search --index` and `--data-dir` together] → `--index` wins, as `--corpus` wins over
  `--config-dir`. This is documented in the help text.

## Migration Plan

All in one pull request. Local commands work after it merges without any action, because the default
data directory is still `data/` and the index is still `data/index.db`. To roll back, revert the commit. The index format doesn't change.
