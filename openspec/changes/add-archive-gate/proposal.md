# Proposal

## Why

The normal flow is to review a change, archive it on its branch, and then merge, so that the code,
spec and archive land as one commit. Nothing enforces that order: PR #3 showed a green merge button
while its change was still active, and it merged before being archived. A required check makes the
workflow something the repository holds to, not something to remember.

## What Changes

- Add a separate check, `archive-check`, that runs on pull requests targeting `main`. It fails when
  a pull request adds or modifies files in an active change under `openspec/changes/`.
- Add a `merge-before-archive` label for the exception, where a change has work that can only happen
  after merge. The label passes this check only, and the `test` check stays required.
- Require `archive-check` in the `main` ruleset, after its first run.
- Update the `tasks` rule in `openspec/config.yaml` to name the label as the exception.
- Document the check and the label in the README.

Out of scope: checking that a change's tasks are complete, because `/opsx:archive` already warns
about that, and adding bypass actors to the ruleset.

## Capabilities

### New Capabilities
<!-- None: this extends the automated checks that continuous-integration already owns. -->

### Modified Capabilities
- `continuous-integration`: Adds a requirement that pull requests can't merge with unarchived
  changes, and one for the labeled exception.

## Impact

- New: `.github/workflows/archive-check.yml`.
- Updated: `openspec/config.yaml` and `README.md`.
- Repository settings: a new `merge-before-archive` label, and `archive-check` added to the required
  status checks in the `main` ruleset.
- Every future change now shows a failing `archive-check` until it is archived. That is expected
  during review, and it is separate from `test`.
- No application code, tests or dependencies change.
