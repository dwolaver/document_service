# Proposal

## Why

The three JSON files that configure the service (`corpus.json`, `ingest_config.json` and
`query_config.json`) sit at the repository root, and the code always reads them from there.
`rfc-ingest` can be pointed at other files with `--corpus` and `--config`, but `rfc-query` has no
override at all. The roadmap's Docker and cloud steps need to run the same code with different
settings, such as a mounted configuration folder and an Ollama server that isn't on `localhost`. At
the moment that would mean editing the version-controlled files.

## What Changes

- **BREAKING** The three configuration files move from the repository root to a `config/`
  directory. Two are renamed, because the `_config` suffix is redundant there: `corpus.json` keeps
  its name, `ingest_config.json` becomes `ingest.json`, and `query_config.json` becomes
  `query.json`. Anything that names the old paths has to change.
- The configuration directory can be selected. The order of precedence is:
  1. a `--config-dir` flag on `rfc-ingest` and `rfc-query`,
  2. the `RFC_QA_CONFIG_DIR` environment variable,
  3. `config/` at the repository root.
- `rfc-ingest` keeps `--corpus` and `--config` for pointing at one file. A file flag takes precedence
  over the directory for that file.
- A configuration directory that doesn't exist fails clearly, naming the directory and where it was
  set.
- The `OLLAMA_BASE_URL` environment variable, when set, overrides `llm.base_url` from the query
  configuration. The other settings still come only from the configuration file.
- Generated data (`data/`, and the index) stays at the repository root. A relative `index_path` still
  resolves from there, whichever configuration directory is in use.
- The programmatic API gains an optional keyword argument for the configuration directory, with the
  same precedence. Callers that pass only the question see no change.

Out of scope: overriding other settings from the environment, which the roadmap's later steps can add
in the same way; configuration formats other than JSON; and moving `data/`.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `project-packaging`: Configuration resolves from a selectable configuration directory, which
  defaults to `config/` at the repository root, instead of from the root itself. Data still resolves
  from the root.
- `answer-generation`: The Ollama address can be overridden by `OLLAMA_BASE_URL`.

## Impact

- Moved: `corpus.json` to `config/corpus.json`, `ingest_config.json` to `config/ingest.json`, and
  `query_config.json` to `config/query.json`.
- Code: `rfc_qa/paths.py` (the default directory, and how a directory is chosen),
  `rfc_qa/ingestion/ingest.py` and `rfc_qa/query.py` (the `--config-dir` flag, the environment
  variables and the API argument).
- Tests: `tests/test_query.py` and `tests/ingestion/test_ingest.py`, plus new tests for precedence and
  for `OLLAMA_BASE_URL`.
- Docs: `README.md` (configuration locations and overrides), and the update-architecture skill's
  list of files to read. `ARCHITECTURE.md` keeps the old paths until the next release regenerates it.
- No new dependencies. CI is unaffected, because the tests don't depend on the developer's
  environment.
