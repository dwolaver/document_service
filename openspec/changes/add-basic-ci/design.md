# Design

## Context

See proposal.md - Why. Requirements are in specs/continuous-integration/spec.md.

The repository is hosted on GitHub and has no `.github/workflows/` directory yet. The test suite
runs offline: 23 tests pass and 1 network integration test is skipped unless
`RFC_DOWNLOADER_NETWORK_TESTS=1` is set. Development uses Python 3.14 and pytest 9.2.0, but
`pytest` is not declared in any requirements file.

There is no `conftest.py` or `pythonpath` setting, and the application modules sit at the
repository root. As a result, `python -m pytest` works, while a bare `pytest` command fails during
collection with import errors.

The `main` ruleset is already active. It requires a pull request, allows squash merges only, has
no bypass actors, and lists no required status checks.

## Goals / Non-Goals

**Goals:**
- A single, fast check that a contributor can reproduce locally with the same commands.
- A stable check name that the `main` ruleset can require.

**Non-Goals:**
- Caching or other speed optimization. The dependency set is small, so it wouldn't pay off yet.
- Reusable workflows or a job matrix, until there is more than one job to share them.

## Decisions

- **GitHub Actions**: The repository is already on GitHub, and Actions reports results directly
  to the pull request and the ruleset without any external service.

- **One workflow, `ci.yml`, with one job, `test`**: The ruleset requires a check by name, so the
  job name is effectively a public contract: renaming it later means updating the ruleset. `test`
  describes what it does and leaves room for later jobs such as `lint` to sit alongside it.

- **Trigger on `pull_request` and `push` to `main`**: The pull request run is the gate. The push
  run confirms the squashed commit that actually landed, which can differ from the branch that was
  tested if `main` moved in between.

- **Separate `requirements-dev.txt`**: It starts with `-r requirements.txt` and adds a pinned
  `pytest==9.2.0`. Adding `pytest` to `requirements.txt` would be simpler, but it would ship a test
  tool in the production image at the Docker step.

- **Run `python -m pytest`**: This matches how the suite passes today and requires no other changes.
  Adding `pythonpath = .` to `pytest.ini` would also fix bare `pytest`, but it isn't needed for CI.
  It can be added on its own if the project moves to a package layout, which is when import setup
  will need revisiting anyway.

- **Single Python 3.14 version**: The project targets one runtime, and the eventual Docker image
  will use one. A version matrix would test compatibility nobody relies on.

- **Leave `RFC_DOWNLOADER_NETWORK_TESTS` unset**: The existing test gate already provides the
  required skip, so no workflow logic or test marker filtering is needed.

- **`permissions: contents: read`, set at workflow level**: The job only needs to check out code.
  An explicit setting makes it read-only regardless of the repository's default token permissions.

- **Pin actions to a major version tag**: This follows the common convention and picks up fixes
  automatically. Pinning to commit SHAs is stronger against supply-chain tampering, but it needs
  regular updates to stay current. That can be revisited once the project has real deployment
  credentials to protect.

## Risks / Trade-offs

- [Python 3.14 is not available on the runner] → `actions/setup-python` fails immediately with a
  clear error, which is caught by the first run on the pull request.
- [The check name must exist before the ruleset can require it] → Add the required status check
  only after the first run, while the pull request is still open.
- [The ruleset has no bypass actors, so a broken workflow would block every merge] → Keep the
  workflow small, and fix it through a pull request. If the check itself is what's broken, an admin
  can temporarily remove it from the ruleset.
- [Requiring a check that never reports leaves a pull request stuck] → The workflow has no path
  filters, so the check reports on every pull request.

## Migration Plan

1. Open a pull request from `add-basic-ci`, which triggers the workflow for the first time.
2. Confirm the `test` check passes, and that its result shows 1 skipped test.
3. Add `test` to the required status checks in the `main` ruleset.
4. Merge the pull request.

To roll back, remove `test` from the ruleset first so that pull requests can still merge, then
revert the workflow through a pull request.
