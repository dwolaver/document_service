# Proposal

## Why

The package finds its configuration and data through the checkout. `paths.py` takes the repository
root as the directory above `src/`, and the defaults are `config/` and `data/` there. So only an
editable install works: a regular install copies the package into site-packages, where that
directory doesn't exist, and the commands fail. To use the service, someone has to clone the
repository and keep the clone, which isn't a reasonable requirement for an installed tool.

## What Changes

- The default configuration files, `corpus.json`, `ingest.json` and `query.json`, move from
  `config/` at the root into the package as `src/rfc_qa/config/`. They ship as package data, and
  the package reads them with `importlib.resources`. The root `config/` directory is removed.
- With no `--config-dir` flag and no `RFC_QA_CONFIG_DIR`, the commands and `query()` read the
  packaged files. A selected directory still has to provide every file the command reads, as now.
  The packaged files aren't used to fill gaps.
- With no `--data-dir` flag and no `RFC_QA_DATA_DIR`, the data directory is the user's data
  directory for `rfc-qa` on their platform, such as `~/.local/share/rfc-qa` on Linux, found with
  `platformdirs`. It used to be `data/` at the repository root. `platformdirs` becomes the second
  runtime dependency.
- The package no longer refers to the checkout at all: `REPO_ROOT` and the "editable installs only"
  limitation are removed. A regular install, from a wheel or with `pip install .`, works from any
  directory with no checkout present.
- Help text and messages name the packaged defaults and the user data directory, instead of
  `config/` and `data/` at the repository root.
- A test builds a wheel, installs it in a fresh virtual environment, and runs `rfc-ingest`,
  `rfc-search` and `rfc-query` from a temporary directory, without network access to document
  sources. CI runs it in the `test` job.
- The README explains how to install the project normally and how to choose the data and
  configuration directories. It also says how a developer keeps using an existing `data/` folder.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `project-packaging`: the defaults for the configuration and data directories, what the repository
  root holds, what a module run reads, and a new requirement that a regular install runs with no
  checkout.
- `continuous-integration`: the checks verify a regular install from a built wheel, outside the
  checkout.

## Impact

- Code: `src/rfc_qa/paths.py` (defaults, no `REPO_ROOT`), the loaders in `query.py` and
  `ingestion/ingest.py` (reading a packaged file as well as a path), and the help text in the
  three commands.
- Files: `config/*.json` move to `src/rfc_qa/config/`.
- Packaging: `pyproject.toml` declares the package data and the `platformdirs` dependency.
  `requirements.txt` pins `platformdirs`.
- Tests: the tests that relied on `REPO_ROOT` and the checkout defaults change. No test may touch the
  real user data directory. There is a new install test.
- CI: the `test` job enables the install test. It needs PyPI access to build the wheel and install
  its dependencies, but not access to document sources.
- Developers: the index in the checkout's `data/` is no longer the default. Move it to the user data
  directory, or set `RFC_QA_DATA_DIR=data`.
- `ARCHITECTURE.md` isn't edited by hand. The update-architecture skill updates it at the next
  release. Its reading list moves to the new config location.
