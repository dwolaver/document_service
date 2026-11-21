# Contributing

[Back to README](README.md)

This guide covers setting up the project, running the tests and checks, and how a change reaches
`main`. To report a security problem, follow [SECURITY.md](SECURITY.md) instead of opening an issue.

## Setting up

The project uses Python 3.14. To install the dependencies and the project's commands, and run the
tests:

```
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

`requirements-dev.txt` installs the project in editable mode, which provides the `rfc-ingest`,
`rfc-query` and `rfc-search` commands. After pulling a change to `pyproject.toml`, run the `pip
install` line again. The code lives in the `rfc_qa` package in `src/`, with a subpackage each for
ingestion, retrieval and generation. The default configuration is in `src/rfc_qa/config/`, and
generated data goes in the user data directory, as described in [Building the
index](docs/usage.md#building-the-index). The commands find both from any directory.

The package is only imported as installed, never from the checkout. The commands, the tests and
module runs such as `python -m rfc_qa.query` all need an install, editable or regular.

## Running the tests

The network integration test is skipped unless `RFC_DOWNLOADER_NETWORK_TESTS=1` is set. The
real-model test is skipped unless `OLLAMA_TESTS=1` is set. It needs Ollama with `llama3.2`, and an
index in the default data directory, or in the one `RFC_QA_DATA_DIR` names. The install tests are
skipped unless `RFC_QA_INSTALL_TESTS=1` is set. They build a wheel, install it with its dependencies
into a fresh virtual environment, and run the three commands from an empty directory, so they need
access to PyPI. CI runs them.

## Lint, format, type and secret checks

The code is linted and formatted with [ruff](https://docs.astral.sh/ruff/) and type-checked with
[mypy](https://mypy-lang.org/), both configured in `pyproject.toml`. A pre-commit hook runs these
checks before each commit, along with a [gitleaks](https://github.com/gitleaks/gitleaks) scan of the
staged changes for secrets. Install it once per clone:

```
pre-commit install
```

The hook runs the tools from the virtual environment, so activate it before committing. To run the
checks on every file, and to fix what ruff can fix:

```
pre-commit run --all-files
ruff format
ruff check --fix
```

The hook only reports problems, and never changes files. mypy runs in strict mode for the `rfc_qa`
package in `src/` and `scripts/`, so every function there needs complete annotations. Tests don't need
annotations, but mypy still checks the bodies of test functions, including `None` handling. A
`# type: ignore` has to name the error it suppresses, such as `# type: ignore[arg-type]`, and mypy
reports one that isn't needed.

pre-commit builds gitleaks from the version pinned in `.pre-commit-config.yaml` the first time the hook
runs, which takes a few seconds and needs network access once. Nothing else needs installing. A
finding stops the commit and shows the file, line and kind of secret, with the value redacted.

If a finding is a real secret, follow [What to do about a leaked secret](SECURITY.md#what-to-do-about-a-leaked-secret).
If a finding has been reviewed and isn't a secret, add the fingerprint from the report, exactly as
printed, as a line in `.gitleaksignore` at the repository root. Only that finding is ignored.

## How a change reaches main

Changes reach `main` through pull requests. On each pull request and each push to `main`, GitHub
Actions runs three checks, without network access to external document sources:

- `test` runs the tests.
- `quality` runs the same lint, format and type checks as the pre-commit hook.
- `secrets` scans every commit the pull request adds, or every commit pushed, with the same gitleaks
  version as the hook. A secret added in one commit and deleted in a later one still fails it.

A pull request can't merge until all three pass, so skipping the hook doesn't get unchecked code or a
secret onto `main`.

Each change adds its entry to [CHANGELOG.md](CHANGELOG.md) under `[Unreleased]`, in the same pull
request, saying what changed for users and contributors. Its OpenSpec task list includes a task for
it.

Each change is reviewed, then archived on its branch, then merged, so that the code, spec and
archive land as one commit. The `archive-check` check enforces this by failing while a pull request
adds or modifies files in an active OpenSpec change, so it's expected to fail during review. If a
change has work that can only happen after merge, the `merge-before-archive` label passes this
check. It doesn't affect any other check, so the tests must still pass.
