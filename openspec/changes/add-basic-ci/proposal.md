# Proposal

## Why

The project is about to grow from two small modules into a RAG pipeline, and tests have only
ever been run by hand on one machine. `main` now requires a pull request, but nothing yet checks
what a pull request contains. Running the existing tests automatically gives every later change
a shared, repeatable gate, and doing it first means the RAG work starts under that gate.

## What Changes

- Add a GitHub Actions workflow that runs the offline test suite on pull requests targeting
  `main` and on pushes to `main`.
- Run on Python 3.14, matching the version the project is developed on.
- Add `requirements-dev.txt`, which includes `requirements.txt` and pins `pytest`. `pytest` is
  used today but is not declared anywhere, so a clean install cannot run the tests.
- Keep the network integration test skipped in CI, so a result never depends on rfc-editor.org
  being reachable.
- After the workflow's first run, add its check to the required status checks in the `main`
  ruleset, so a failing change cannot be merged. This is a repository setting rather than a file
  in this change, so it is recorded here as a manual step.
- Note the CI gate in the README roadmap and document how to run the tests.

Out of scope: linting, type checking, coverage gates, multiple Python versions, Docker, and
deployment. Later changes can add these.

## Capabilities

### New Capabilities
- `continuous-integration`: The automated checks that run against proposed and merged changes,
  including when they run, what they verify, and how they gate `main`.

### Modified Capabilities
<!-- None: the runtime behavior of rfc-downloader and query-interface is unchanged. -->

## Impact

- New: `.github/workflows/ci.yml` and `requirements-dev.txt`.
- Updated: `README.md`.
- New development dependency: `pytest`. It stays out of `requirements.txt`, so it will not be
  included in the production image.
- No changes to application code or tests.
- Repository settings: the `main` ruleset gains a required status check.
