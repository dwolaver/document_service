# Proposal

## Why

The service code is in an `rfc_qa/` directory at the repository root, beside `config/`, `scripts/`,
`tests/` and `openspec/`. Nothing in that name says it's the source code, so a reader has to open it
to find out. The standard `src` layout puts the package in `src/`, where Python developers expect to
find it. It also stops the uninstalled checkout from being imported by accident: tests and commands
can only use the package as it is installed, which is how the project already says it must be used.

## What Changes

- Move the `rfc_qa` package, unchanged, from `rfc_qa/` to `src/rfc_qa/`, keeping its history.
- Package discovery in `pyproject.toml` looks in `src/`. The package name, the import paths and the
  three commands stay the same.
- The repository root is still found from the package, now two directories above it, so `config/`
  and `data/` keep working as defaults from any directory. A test checks that it really is the
  repository root.
- mypy finds the package in `src/`, and keeps checking `scripts/` and `tests/` as before.
- Running a command as a module, such as `python -m rfc_qa.query`, needs the project to be
  installed, as the commands already do. It no longer works from an uninstalled checkout. An
  existing editable install has to be reinstalled once after the move.
- The README, the update-architecture skill's reading list, and comments that name the package's
  location point to `src/rfc_qa`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `project-packaging`: the package lives in `src/rfc_qa`, the repository root holds `src/` instead
  of the package, and running a command as a module needs the project installed.

## Impact

- Code: every file under `rfc_qa/` moves to `src/rfc_qa/`. Only `paths.py` changes, in how it finds
  the repository root and in its docstring.
- Configuration: `pyproject.toml` (package discovery, mypy), and comments in `pytest.ini`.
- Tests: `tests/test_paths.py` gains a check of the repository root. `tests/test_packaging.py`
  updates a comment. Test imports don't change.
- Developers: run `pip install -r requirements-dev.txt` again after pulling, or the old editable
  install keeps pointing at the removed `rfc_qa/` directory.
- CI: no workflow change. The jobs already install the project before running the tests and checks.
- `ARCHITECTURE.md` isn't edited by hand. The update-architecture skill brings it up to date at the
  next release.
