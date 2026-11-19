# Proposal

## Why

All seven service modules sit at the repository root next to configuration, data, scripts and
tests. Nothing in the layout shows which module belongs to which stage. Code can only be imported
when the repository root is on `sys.path`, which is why the README tells people to use
`python -m pytest`. The roadmap adds more retrieval backends and more generation logic, and each new
module would add to the clutter at the root. Moving to a package now, while there are only seven
modules, keeps the move small.

## What Changes

- **BREAKING** The service modules move into a package, `rfc_qa`, with one subpackage per stage:
  - `rfc_qa.ingestion`: `rfc_downloader`, `rfc_parser`, `chunker` and the `ingest` pipeline.
  - `rfc_qa.retrieval`: `keyword_index`.
  - `rfc_qa.generation`: `answer_generator`.
  - `rfc_qa.query` stays at the package top level, because it combines retrieval and generation.
  - The `Chunk` type moves to a shared top-level module, `rfc_qa.chunk`, because all three stages
    use it.
- **BREAKING** `python ingest.py`, `python query.py` and `python keyword_index.py` no longer exist.
  A new `pyproject.toml` installs three commands, `rfc-ingest`, `rfc-query` and `rfc-search`. Each
  can also be run as a module, for example `python -m rfc_qa.query`.
- Configuration (`corpus.json`, `ingest_config.json`, `query_config.json`) and generated data
  (`data/`) stay at the repository root and keep resolving from there, whatever the working
  directory.
- Messages that tell the user to run ingestion name the new command.
- CI installs the project as well as its dependencies, so a broken package definition or missing
  command fails the checks.
- Tests, the README and the update-architecture skill switch to the new import paths and commands.

Out of scope: changing any behavior of ingestion, retrieval, generation or querying; moving
`scripts/update_architecture.py`, which is release tooling rather than part of the service;
publishing the package; and regenerating `ARCHITECTURE.md`, which waits for the next release.

## Capabilities

### New Capabilities
- `project-packaging`: How the service is organized into a package with stage subpackages, how it
  is installed, which commands it provides, and where those commands find configuration and data.

### Modified Capabilities
- `continuous-integration`: The clean-environment check installs the project itself and fails if
  the project can't be installed.

## Impact

- Moved: every root `.py` module except the release script, into `rfc_qa/`. Imports change
  throughout.
- New: `pyproject.toml`, and `__init__.py` files for the package and subpackages.
- Updated: `requirements-dev.txt` (installs the project in editable mode), all test modules (import
  and monkeypatch targets), `README.md` (setup and commands), and
  `.claude/skills/update-architecture/SKILL.md` (where to read the code).
- Anyone who imports the root modules or runs the old commands has to switch. The project has no
  external users yet, so this affects only local habits and documentation.
- No new runtime dependencies. Building the editable install uses setuptools, which pip fetches.
- `ARCHITECTURE.md` will name the old paths until the next release regenerates it.
