# Design

## Context

`rfc_qa/paths.py` defines `REPO_ROOT` and fixed paths to the three configuration files at the root.
The two commands use them differently:

- `rfc-ingest` takes `--corpus` and `--config` flags, which default to `paths.CORPUS_PATH` and
  `paths.INGEST_CONFIG_PATH`, and passes explicit paths to `run_ingestion(corpus_path, config_path,
  data_dir)`.
- `rfc-query` has no flags beyond the question. `query(user_query)` reads the module attribute
  `CONFIG_PATH`, which tests monkeypatch. `load_query_config(path)` validates the file and resolves a
  relative `index_path` from `REPO_ROOT`.

The code reads no environment variables. The Ollama address reaches the model as
`ModelSettings.base_url`, built from `llm.base_url` in `load_query_config`.

## Goals / Non-Goals

**Goals:**
- One rule for finding configuration, shared by both commands and the API, with the precedence in
  the project-packaging spec.
- Overrides that read the environment when they're used, not at import time, so tests can control
  them.
- A test suite that gives the same result whatever `RFC_QA_CONFIG_DIR` or `OLLAMA_BASE_URL` is set to
  in the developer's shell.

**Non-Goals:**
- A general mechanism for overriding any setting from the environment. `OLLAMA_BASE_URL` is the only
  setting override. Later roadmap steps can add others the same way.
- Letting `OLLAMA_BASE_URL` stand in for a missing `llm.base_url`. The version-controlled file stays
  complete and valid on its own.

## Decisions

### Layout: `config/` with shorter file names

```
config/
  corpus.json      was corpus.json
  ingest.json      was ingest_config.json
  query.json       was query_config.json
```

Inside `config/`, the `_config` suffix is redundant, so the two configuration files drop it.
`corpus.json` keeps its name. The files move with `git mv` and their content doesn't change, so git
still detects each move as a rename and keeps its history.

Archived designs keep the old names: they record what was true when they were written.
`ARCHITECTURE.md` picks up the new names when the next release regenerates it.

Alternative: keep the old names inside `config/`. That would keep the names that archived designs and
`ARCHITECTURE.md` use, but the suffix says nothing once the directory says it. Rejected by the
repository owner.

### Resolving the directory in `rfc_qa/paths.py`

`paths.py` gains:

- `DEFAULT_CONFIG_DIR = REPO_ROOT/config`, `CONFIG_DIR_ENV = "RFC_QA_CONFIG_DIR"`, and the three
  file names as constants.
- `resolve_config_dir(explicit=None, explicit_source="--config-dir") -> ConfigDir`, a small frozen
  dataclass holding `path` and `source`. The order is: `explicit` if given, then the environment
  variable if it's set and not empty, then the default. Flag and environment values go through
  `os.path.abspath`, so a relative path resolves from the working directory, as `--corpus` already
  does. If the directory doesn't exist, it raises `ConfigDirError` (a `ValueError`) with a message
  such as: `Configuration directory '/x' (from RFC_QA_CONFIG_DIR) doesn't exist.`

The fixed `CORPUS_PATH`, `INGEST_CONFIG_PATH` and `QUERY_CONFIG_PATH` are removed, so that nothing
can read a configuration file without going through the resolution. `DATA_DIR` and `INDEX_PATH`
stay.

Alternative: resolve a relative environment or flag path from the repository root. Rejected because
every command-line tool, and this project's own `--corpus`, resolves relative paths from the working
directory. A container also usually sets an absolute path.

### `rfc-ingest`: resolve the directory only when a file comes from it

`--config-dir` is added. `--corpus` and `--config` now default to `None`. When either is missing,
`main` resolves the configuration directory and takes that file from it. When both are given, the
directory isn't resolved at all. So a stale `RFC_QA_CONFIG_DIR` doesn't block a run that doesn't use
it, and a missing directory still fails whenever a file would have been read from it.

`ConfigDirError` is reported like an `IngestError`: one line on stderr, exit code 1, before any
download. `run_ingestion(corpus_path, config_path, data_dir)` doesn't change.

### `rfc-query` and the API

- `query(user_query, *, config_dir=None)` gains a keyword-only argument. It resolves with
  `explicit_source="config_dir argument"` and reads `query.json` from the result. A
  `ConfigDirError` becomes a `CONFIG_INVALID` failure response. No new error code is needed, so the
  numbering is untouched.
- `main` adds `--config-dir`. It resolves the directory itself, with the source label
  `--config-dir`, so the message names the flag the user typed. On error it prints to stderr and
  exits 1, like any other failure. Otherwise it passes the resolved path to `query`.
- The module attribute `CONFIG_PATH` is removed. Tests select configuration through `config_dir`, or
  through the environment variable, like real callers.
- `load_query_config(path)` keeps its signature. A relative `index_path` still resolves from
  `REPO_ROOT`, as the modified data requirement says.

### `OLLAMA_BASE_URL` in `load_query_config`

After validating `llm.base_url`, `load_query_config` uses `os.environ.get("OLLAMA_BASE_URL")` instead
when it's set and not empty. Doing this in the loader rather than in `answer_generator` keeps the
generator free of environment lookups, and the resulting `ModelSettings` shows the address actually
used. The existing "Ollama not running" message names `settings.base_url`, so it reports the
overridden address without any change.

No URL validation is added. The configured value isn't validated beyond being a non-empty string
either, and a wrong address already fails clearly as "model unavailable".

### Keeping the tests independent of the shell

A new `tests/conftest.py` has an autouse fixture that removes `RFC_QA_CONFIG_DIR` and
`OLLAMA_BASE_URL` with `monkeypatch.delenv(..., raising=False)`. Tests that need a variable set it
themselves. Without this, a developer with `OLLAMA_BASE_URL` exported would see the configuration
tests fail locally while CI passed.

`tests/test_paths.py` is new, matching `rfc_qa/paths.py` under the mirrored layout. It covers the
precedence, empty-variable, relative-path and missing-directory cases directly.

## Risks / Trade-offs

- [Scripts or habits that name the old root paths break] → Covered by the **BREAKING** note and the
  README. The only callers are the README, the update-architecture skill and the tests, and all of
  them are updated.
- [A copied configuration directory missing one of the three files gives a "Failed to read" error
  rather than a missing-directory error] → The existing loaders already name the file they couldn't
  read, which is enough to act on. Checking all three up front would make `rfc-query` depend on
  ingestion files it never reads.
- [`OLLAMA_BASE_URL` left set in a shell silently redirects local queries] → It only takes effect
  when set. The "model unavailable" message names the address it tried, which makes an unintended
  override easy to spot. The README documents the variable.
- [`ARCHITECTURE.md` shows the old paths] → Accepted until the next release, as before. The skill's
  list of files to read is updated in this change.

## Migration Plan

All in one pull request. After it merges, local commands work without any action, because the
defaults move with the files. Anyone keeping private copies of the configuration points
`RFC_QA_CONFIG_DIR` or `--config-dir` at them. To roll back, revert the commit. The index format and
`data/` are untouched.
