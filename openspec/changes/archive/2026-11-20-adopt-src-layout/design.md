# Design

## Context

The package is at `rfc_qa/` at the repository root. Three things depend on that location as well as
the imports:

- `rfc_qa/paths.py` finds the repository root as the directory above the package. `config/` and
  `data/` default to folders there.
- `pyproject.toml` finds the package with `[tool.setuptools.packages.find] include = ["rfc_qa*"]`,
  and mypy checks `files = ["rfc_qa", "scripts", "tests"]` with `explicit_package_bases`.
- `pytest.ini` sets `pythonpath = .` so tests can import `scripts/`. Because the package is also at
  the root, it makes the checkout importable even without an install.

The tests that check the default directories compare them with `paths.REPO_ROOT` itself, so a wrong
`REPO_ROOT` wouldn't make them fail.

## Goals / Non-Goals

**Goals:**

- The package is at `src/rfc_qa`, and only the installed package is ever imported.
- Nothing a user sees changes: command names, flags, output, import paths and default directories
  stay the same.

**Non-Goals:**

- Moving `scripts/` or `tests/`. The release script isn't part of the installed package, and the
  tests stay at the root where pytest and CI find them.
- Editing `ARCHITECTURE.md`. Under the architecture-docs spec only the pinned model writes it, and
  the update-architecture skill brings it up to date at the next release.
- Changing archived OpenSpec records, which describe the code as it was.

## Decisions

### Move with `git mv`, without changing the modules

The modules move as they are, so `git log --follow` and blame keep their history and the diff shows
renames. Only `paths.py` changes, for the next decision. Splitting the move and the edit into two
commits isn't needed, because the pull request is squash-merged into one commit anyway.

### Find the repository root two directories above the package

`REPO_ROOT` becomes the directory two levels above `paths.py`'s package (`src/rfc_qa` → `src` → the
root), still computed from `__file__`. This works because only editable installs are supported, so
`__file__` is always in the checkout.

A new test checks that `REPO_ROOT` contains `pyproject.toml` and `config/`. Without it, a wrong
`REPO_ROOT` would still pass the existing tests and only fail when a command runs.

Alternatives: searching upward from `__file__` for `pyproject.toml` works wherever the package sits,
but it's more code for a layout that won't change again, and it could find the wrong file in an
unusual checkout. Keeping a marker file is the same idea with an extra file.

### Point setuptools and mypy at `src/`

- setuptools: `where = ["src"]` with `include = ["rfc_qa*"]`. The `include` stays, so nothing else
  in `src/` could become a package.
- mypy: `files = ["src", "scripts", "tests"]` and `mypy_path = "src"`. In a scratch copy, mypy
  without `mypy_path` reported 43 `import-not-found` errors, because it doesn't follow the editable
  install's import hook. With `mypy_path` it found no issues. The checks are as strict as before.
- ruff needs no change: by default it treats `src/` as a source root, and in the scratch copy the
  lint and format checks passed, with import sorting unchanged.

### Require an install to run anything

The user chose this. `pytest.ini` keeps `pythonpath = .` for `scripts/`, but since the root no
longer contains the package, tests import `rfc_qa` from the editable install, like the commands do.
`src` isn't added to `pythonpath`, because that would bring back imports of the uninstalled
checkout, which this change removes. In a scratch copy, an editable install ran
`python -m rfc_qa.query --help` from `/tmp`, and an environment without the install reported
`No module named 'rfc_qa'` from the repository root.

`tests/test_packaging.py` already skips its install checks when the project isn't installed. Other
tests now fail at import in that case, which is the intended result. CI is unaffected, because
`requirements-dev.txt` includes `-e .`.

## Risks / Trade-offs

- [An existing editable install points at the removed `rfc_qa/` directory, so imports fail or the
  commands break after pulling] → The README already says to run the `pip install` line again after
  a change to `pyproject.toml`. This change makes that more prominent, and the pull request says so.
- [A leftover `rfc_qa/` directory of `__pycache__` files at the root after the move] → It holds
  only untracked, ignored files, and it can't be imported as a package without `__init__.py`. The
  apply step removes it from the working copy so the root listing matches the spec.
- [A leftover `rfc_qa.egg-info/` at the root] → It's ignored by git. The new install writes its
  metadata under `src/`. Remove the old one locally.
