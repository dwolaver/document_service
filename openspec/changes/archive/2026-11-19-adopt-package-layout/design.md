# Design

## Context

The service is seven flat modules at the repository root. They import one another by bare name
(`from chunker import Chunk`). Three of them find configuration and data from their own location:

- `ingest.py`: `_ROOT = dirname(__file__)` for `corpus.json`, `ingest_config.json` and `data/`.
- `keyword_index.py`: `DEFAULT_INDEX_PATH` is `data/index.db` next to the module.
- `query.py`: `_ROOT` for `query_config.json`, and to resolve a relative `index_path`.

Tests import the modules by bare name. They monkeypatch module attributes (`ingest.download_rfc`,
`query.generate_answer`, `query.CONFIG_PATH`, `answer_generator._post_chat`,
`rfc_downloader.requests`) and use `dirname(query.__file__)` as the repository root. CI runs
`pip install -r requirements-dev.txt` and then `python -m pytest`, which works only because
`python -m` puts the working directory on `sys.path`.

`Chunk` is defined in `chunker.py`, but `keyword_index.py` (retrieval), `query.py` and the
generation tests use it too.

`scripts/update_architecture.py` is release tooling. It already imports as `scripts.update_architecture`
and refers to no service module.

## Goals / Non-Goals

**Goals:**
- Each module's location shows which stage it belongs to, and the subpackages don't depend on one
  another in a cycle.
- No behavior changes other than the command names and the messages that name them.
- `git log --follow` keeps working on every moved module.

**Non-Goals:**
- A distributable wheel. The project is installed in editable mode from a checkout. A regular
  (non-editable) install isn't supported, because configuration and data live in the checkout.
- Renaming modules within their subpackages, or splitting or merging modules.
- Reorganizing `tests/` into a tree that mirrors the package.

## Decisions

### Flat package at the repository root, not a `src/` layout

`rfc_qa/` sits at the repository root. A `src/` layout guards against testing the checkout instead
of the installed package. That guard matters for distributed libraries, and this project is only
ever run from its checkout. The flat layout keeps `python -m rfc_qa.query` and `python -m pytest`
working from the root without an install, as the project-packaging spec requires, and the
repository root stays exactly one directory above the package.

Alternative: `src/rfc_qa/`. Rejected because module runs would need an install or `PYTHONPATH`, and
the repository root would be two levels up, which is easier to get wrong.

### Module placement

```
rfc_qa/
  __init__.py
  paths.py              repository root and default file locations
  chunk.py              Chunk (moved out of chunker.py)
  query.py              programmatic entry point and rfc-query
  ingestion/
    __init__.py
    rfc_downloader.py
    rfc_parser.py
    chunker.py
    ingest.py           pipeline and rfc-ingest
  retrieval/
    __init__.py
    keyword_index.py    build_index, search, read_metadata and rfc-search
  generation/
    __init__.py
    answer_generator.py
```

- **Module names are kept.** `rfc_downloader` inside `ingestion` is slightly redundant, but keeping
  the names makes each move a pure `git mv` with import edits. It also keeps the names that specs,
  archived designs and `ARCHITECTURE.md` use. Renaming can happen later if it seems worth it.
- **`keyword_index` belongs to retrieval, including `build_index`.** Ingestion calls `build_index`,
  but the recorded key decision is that all SQL and the retrieval boundary live in one module. That
  module therefore belongs to the stage that owns the index format.
- **`Chunk` moves to `rfc_qa/chunk.py`.** If it stayed in `ingestion.chunker`, retrieval would
  import from ingestion while ingestion imports from retrieval (`build_index`). That's a cycle
  between subpackages, though not between modules. As a neutral top-level module, `chunk.py` gives a
  one-way graph: `ingestion → retrieval → chunk` and `query → retrieval, generation`. `chunker.py`
  imports `Chunk` from it. It doesn't re-export it, so that every import uses one path.
- **`query.py` stays top-level.** It is the composition of retrieval and generation, and the specs
  call it the service's main entry point. Putting it in either stage would make that stage import
  the other.
- **Subpackage `__init__.py` files stay empty.** Re-exporting every public name would add a second
  import path and make monkeypatching harder to get right. Callers import from the module.

Imports inside the package are absolute (`from rfc_qa.retrieval.keyword_index import build_index`),
in keeping with the explicit style already used in the code.

### One place for the repository root

`rfc_qa/paths.py` defines `REPO_ROOT = dirname(dirname(abspath(__file__)))`, along with the default
locations: `CORPUS_PATH`, `INGEST_CONFIG_PATH`, `QUERY_CONFIG_PATH`, `DATA_DIR` and `INDEX_PATH`.
`ingest`, `keyword_index` and `query` take their defaults from it instead of each working the root
out on its own. The module attributes that tests patch (`query.CONFIG_PATH`,
`ingest.DEFAULT_*`, `keyword_index.DEFAULT_INDEX_PATH`) stay in their modules, assigned from
`paths`, so patching works as before.

Because the editable install points at the checkout, `__file__` resolves into the checkout and the
root is found whatever the working directory.

Alternative: resolve from the working directory. Rejected because it changes behavior: commands
would fail when run from anywhere but the root.

### pyproject.toml with setuptools and console scripts

```toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "rfc-qa"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["requests"]
license = "MIT"

[project.scripts]
rfc-ingest = "rfc_qa.ingestion.ingest:main"
rfc-query = "rfc_qa.query:main"
rfc-search = "rfc_qa.retrieval.keyword_index:main"

[tool.setuptools.packages.find]
include = ["rfc_qa*"]
```

- Each existing `main(argv=None)` already returns an exit code, and console-script wrappers pass it
  to `sys.exit`, so no entry-point code changes. Each module keeps its `if __name__ == "__main__"`
  block for `python -m`. The argparse usage line shows `rfc-query` instead of `query.py`. That's
  the intended rename, not a behavior change.
- `packages.find` is limited to `rfc_qa*` so that `tests` and `scripts` aren't packaged. Without
  the limit, setuptools refuses a flat layout that has several top-level packages.
- **Pins stay in `requirements.txt`.** `pyproject.toml` declares `requests` without a version, and
  `requirements.txt` keeps the exact pin that CI and development install. `requirements-dev.txt`
  gains `-e .`, so the existing `pip install -r requirements-dev.txt` also installs the package and
  its commands, and the CI workflow file doesn't change.
- The version is `0.1.0` to match the current release tag. Release tooling doesn't read it.

Alternatives: hatchling or flit. Both would work. setuptools needs no extra configuration for a
flat layout beyond `packages.find`, and it is what pip already uses.

### Proving the commands exist

`pip install -e .` succeeds even when a script's target doesn't exist, because the wrapper is only
resolved at run time. A new test, `tests/test_packaging.py`, reads the `rfc-qa` distribution's
console-script entry points through `importlib.metadata`. It asserts that there are exactly these
three and that each one loads to a callable. With CI installing the project, this test is what
fails the checks when a command is broken, as the modified continuous-integration requirement
needs. The same file checks that no service module is left at the repository root: no `*.py` at
the root other than what's allowed, which today is nothing.

The test needs the project installed. Like the existing gated tests, it skips with a clear reason
when the distribution isn't found, so a bare checkout can still run the suite. CI always installs
the project, so the test always runs there.

### Messages naming the ingestion command

`keyword_index.py` ("Run ingest.py to build it.") and `query.py` ("Build it with
`python ingest.py`.") change to name `rfc-ingest`. `tests/test_query.py::test_missing_index`
asserts the new text.

## Risks / Trade-offs

- [Stale `.pyc` files or an old `__pycache__` at the root shadow nothing, but leftover root modules
  would] → `git mv` removes the originals, and the packaging test fails if any service module is
  left at the root.
- [Monkeypatch targets silently stop working if a test patches the wrong module, for example
  patching `chunker.Chunk` after the move] → Tests patch the module that looks the name up
  (`rfc_qa.ingestion.ingest.download_rfc`, `rfc_qa.query.generate_answer`), as they do today. The
  full suite has to pass with no new skips.
- [Developers with an existing venv won't have the commands until they reinstall] → The README's
  setup steps already run `pip install -r requirements-dev.txt`, which now includes `-e .`. The
  pull request description says to rerun it.
- [A regular `pip install .` would put the package in site-packages, where `REPO_ROOT` points at
  the wrong place] → Not supported, per the non-goals. `paths.py` documents this. Supporting it
  would need configurable paths, which is out of scope.
- [`ARCHITECTURE.md` describes the old layout until the next release] → Accepted, as in earlier
  changes. The update-architecture skill is told where the code now lives, so the next run
  describes the package.
- [The editable install builds in an isolated environment and fetches setuptools] → CI already has
  network access to PyPI for its dependencies, so this adds no new kind of dependency.

## Migration Plan

All in one pull request: move the modules, fix the imports, add the packaging files, update the
tests and documentation. After merge, each developer reruns `pip install -r requirements-dev.txt`.
To roll back, revert the commit. Nothing persistent changes: `data/` and the index format are
untouched, so an existing index keeps working without rerunning ingestion.
