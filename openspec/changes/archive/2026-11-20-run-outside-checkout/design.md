# Design

## Context

`src/rfc_qa/paths.py` defines `REPO_ROOT` as three directories above itself, and the defaults
`DEFAULT_CONFIG_DIR = REPO_ROOT/config` and `DEFAULT_DATA_DIR = REPO_ROOT/data`. `SelectedDir(path,
source)` holds the chosen directory as a string, and `.file(name)` joins a file name to it. The
loaders, `load_query_config(path)` in `query.py` and `load_corpus` and `load_config` in
`ingestion/ingest.py` (through `_load_json`), take a string path and `open()` it. Their errors name
the path.

The tests compare defaults with `paths.REPO_ROOT` and `paths.DEFAULT_CONFIG_DIR`, and read the real
configuration files through them. `tests/conftest.py` clears `RFC_QA_CONFIG_DIR`, `RFC_QA_DATA_DIR`
and `OLLAMA_BASE_URL` for every test.

Ingestion reuses an RFC file already in `<data dir>/rfcs/` instead of downloading it. That is what
lets the install check build an index without network access.

## Goals / Non-Goals

**Goals:**

- The package doesn't refer to the checkout. Everything it reads by default is either inside the
  installed package or in the user data directory.
- Flags, variables and `query()` arguments keep their current names, precedence and errors.

**Non-Goals:**

- Publishing to PyPI or tagging a release. A wheel can be built and installed, and that's all this
  change needs.
- Moving an existing index automatically. The project isn't deployed, so only developers'
  checkouts have one, and the README says how to keep using it.
- A command that writes the packaged defaults out for editing. The README shows where they are, so
  they can be copied into a directory for `--config-dir`.
- Windows and macOS runs in CI. `platformdirs` handles those platforms. CI runs on Linux, as now.

## Decisions

### Ship the defaults in `src/rfc_qa/config/`

The three files move with `git mv` to `src/rfc_qa/config/`, and `pyproject.toml` declares them with
`[tool.setuptools.package-data] rfc_qa = ["config/*.json"]`. `config/` stays a plain data directory,
without an `__init__.py`. Declaring the files explicitly is more reliable than
`include-package-data`, which depends on files being tracked or listed in `MANIFEST.in`. The install
test checks that the wheel really contains them.

Alternative: keep `config/` at the root and have the build copy it in. The user rejected this,
because it leaves two copies to keep in step.

### Read configuration through `importlib.resources`

The default configuration directory is `importlib.resources.files("rfc_qa") / "config"`, a
`Traversable`. A directory from `--config-dir` or `RFC_QA_CONFIG_DIR` becomes a `pathlib.Path`, which
is also a `Traversable`. So the selected configuration directory holds a `Traversable` and its source
(the flag, the variable, the `config_dir` argument, or `packaged defaults`), and `.file(name)`
returns `location / name`.

The loaders accept `str | Traversable`, turn a string into a `Path`, and read with
`.open(encoding="utf-8")`. Tests and callers that pass a string path keep working. Errors still name
the file, as `str()` of it, and that's a real path for every install pip makes.

`query(config_dir=...)` keeps taking a string. `rfc-query` still resolves the directory itself, so
that an error names the flag. It passes the path on only when a flag or variable chose it, and
passes `None` for the packaged defaults, so `query()` resolves the same default.

The data directory doesn't change shape. It stays a string path, because ingestion writes to it.

Alternatives:

- `str(files("rfc_qa") / "config")` used as an ordinary path. It's less code, but it only works when
  the package is a directory on disk, and it uses `importlib.resources` only to find the package.
- `importlib.resources.as_file()`, which makes a real path available. That path only lasts while a
  context manager is open, so it would have to wrap every command.

### Default the data directory with `platformdirs`

The default is `platformdirs.user_data_dir("rfc-qa", appauthor=False)`. That's
`$XDG_DATA_HOME/rfc-qa`, or `~/.local/share/rfc-qa`, on Linux, and the platform's equivalent on
macOS and Windows. `appauthor=False` avoids a nested `rfc-qa\rfc-qa` folder on Windows. The function
is called when a directory is resolved, not when the module is imported, so a change to the
environment takes effect and tests can redirect it. `ensure_exists` isn't used, because ingestion
already creates the directory and a query shouldn't.

`platformdirs` is added to `[project] dependencies` and pinned as `platformdirs==4.14.8` in
`requirements.txt`. It's MIT-licensed, ships type hints (`py.typed`), supports Python 3.11 and later,
and has no dependencies of its own.

Alternatives: `./data` under the working directory, which the user rejected because a query from
another directory wouldn't find the index; or writing the platform rules by hand, which duplicates
what `platformdirs` does and is easy to get wrong on macOS and Windows.

### Remove `REPO_ROOT` from the package

`REPO_ROOT`, `DEFAULT_CONFIG_DIR` and `DEFAULT_DATA_DIR` as checkout paths are removed, along with
the docstring's "editable installs only" paragraph. The tests that need the repository root, such as
the root listing in `tests/test_packaging.py`, compute it from their own location in a shared
`tests` helper. The test that checked `REPO_ROOT` is replaced by tests that check:

- the packaged configuration directory is inside the imported `rfc_qa` package and holds the three
  files;
- the default data directory is what `platformdirs` returns for `rfc-qa`.

Tests that read the real configuration go through the packaged directory.

### Keep tests out of the real user data directory

An autouse fixture in `tests/conftest.py` points the default data directory at a temporary
directory, by patching the function in `paths` that calls `platformdirs`. A test that checks the real
default undoes the patch and only compares paths. It never writes. Without the fixture, a test that
runs ingestion with no data directory would write to the developer's real data folder.

### Check a regular install in a test, run by CI

`tests/test_install.py` has one test, marked `install` and skipped unless `RFC_QA_INSTALL_TESTS=1`,
because it needs PyPI and takes some seconds. It:

1. Builds a wheel from the repository with `pip wheel --no-deps`, and checks that it contains
   `rfc_qa/config/*.json` and nothing outside `rfc_qa`.
2. Creates a fresh venv in a temporary directory, without system site-packages, and installs the
   wheel with its dependencies.
3. Runs the commands with `cwd` set to an empty temporary directory, `HOME` and `XDG_DATA_HOME`
   set to temporary directories, and `RFC_QA_CONFIG_DIR` and `RFC_QA_DATA_DIR` unset.
   `OLLAMA_BASE_URL` points to an address nothing listens on, so no local Ollama answers.
4. Reads the packaged `corpus.json` with the venv's Python through `importlib.resources`, and saves
   a test fixture RFC under each corpus number in `<user data dir>/rfcs/`. Ingestion then reuses
   these files instead of downloading.
5. Expects `rfc-ingest` to succeed, `rfc-search` to find a word from the fixture, and `rfc-query` to
   exit 1 with the model-unavailable message. A configuration or missing-index error fails the test.
6. Checks that the imported `rfc_qa` is in the venv's site-packages, not the checkout.

CI's `test` job sets `RFC_QA_INSTALL_TESTS=1`, so this runs under the existing required `test` check
and the ruleset doesn't change. The job already has PyPI access, which pip needs. It still has no
access to document sources: the RFCs come from the fixture, which the
continuous-integration spec requires.

Alternatives: a separate CI job, which would be a new required check for the owner to add to the
ruleset; or a shell script in the workflow, which a developer couldn't run the same way locally.

### Help text and messages

The `--config-dir` help says the default is `$RFC_QA_CONFIG_DIR`, then the packaged defaults. The
`--data-dir` help says `$RFC_QA_DATA_DIR`, then the user data directory, and gives the resolved
path. A missing-index message already names the full index path, so the user can see where the
default is.

## Risks / Trade-offs

- [A developer's existing index in the checkout's `data/` is no longer found] → The README says to
  move it with `mv data ~/.local/share/rfc-qa` on Linux, or to set `RFC_QA_DATA_DIR=data`. The
  missing-index message names the new path. `data/` stays in `.gitignore`.
- [The Ollama-gated test (`OLLAMA_TESTS=1`) expects an index in the default data directory] → It
  now reads the user data directory. The README's Development section, which doesn't mention this
  test yet, gains a line saying what it needs.
- [The install test needs PyPI, so it fails offline] → It's skipped unless `RFC_QA_INSTALL_TESTS=1`,
  and CI has PyPI access.
- [A second runtime dependency] → `platformdirs` is small, typed and widely used, and the version is
  pinned like `requests`.
- [Packaged defaults are inside site-packages after a regular install, which users shouldn't edit]
  → The README tells users to copy them into a directory and select it with `--config-dir` or
  `RFC_QA_CONFIG_DIR`. In an editable install, the files in `src/rfc_qa/config/` are the ones read,
  so developers edit them in place.
