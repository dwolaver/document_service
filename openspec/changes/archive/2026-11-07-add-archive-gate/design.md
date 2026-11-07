# Design

## Context

See proposal.md - Why. Requirements are in specs/continuous-integration/spec.md.

`.github/workflows/ci.yml` has one job, `test`, which the `main` ruleset requires. The ruleset has no
bypass actors, so a failed required check blocks everyone, including the repository owner. Active
changes live in `openspec/changes/<name>/`, and archived ones in `openspec/changes/archive/`.

The planned detection command was run against the repository's real history. It flags PRs #1 and #3,
which added active changes, and passes PRs #2 and #4, which only archived them.

## Goals / Non-Goals

**Goals:**
- A blocked merge that clearly means "not archived yet", separate from test results.
- An exception that is visible on the pull request and can't let failing tests through.

**Non-Goals:**
- Checking that tasks are complete, or that specs were synced. `/opsx:archive` handles those.
- Running `openspec validate` in CI, which would add an install for little benefit here.
- Blocking pushes to `main`, which the ruleset already does.

## Decisions

- **A separate workflow, `archive-check.yml`, with one job named `archive-check`**: Label changes have
  to re-run this check, and they shouldn't re-run the tests, so it doesn't belong in `ci.yml`. It also
  needs no Python. The job name is the required check's name, so renaming it means updating the
  ruleset. It only runs on pull requests, because the ruleset blocks direct pushes.

- **Check what the pull request changes, not the whole tree**: The check diffs the pull request
  against its base. Checking whether `openspec/changes/` is empty would be simpler, but after an
  exception merge, every unrelated pull request would fail until that change was archived.

- **Detection is one `git diff`**:

  ```
  git diff --name-only --no-renames --diff-filter=d "$BASE...$HEAD" \
    -- openspec/changes/ ':(exclude)openspec/changes/archive/'
  ```

  `--no-renames` reports an archive move as a deletion plus an addition, and `--diff-filter=d` drops
  the deletion, while the exclusion drops the addition. Any output fails the check, and the files
  are printed so that the failure explains itself. The three-dot form compares against the merge
  base, so commits that land on `main` after the branch started don't count. Checkout needs
  `fetch-depth: 0` for that merge base to exist.

- **Inline shell rather than a Python script**: The logic is one command and one condition, so a
  script with its own tests would be more code than the behavior it protects. The history test above
  and the pull request scenarios verify it instead.

- **Trigger on `opened`, `synchronize`, `reopened`, `labeled` and `unlabeled`**: The first three are
  the default pull request events, and the last two make label changes take effect with no new
  commit. A new run on the same commit replaces the earlier result for the required check. There are
  no path filters, because a required check that never reports leaves a pull request stuck.

- **A label for the exception, not a ruleset bypass**: A bypass skips every rule, so failing tests
  could merge too. The label passes only this check, stays visible on the pull request, and can only
  be set by people with triage access or above. `merge-before-archive` says what it permits.

- **Pass label and SHAs through `env`**: Values reach the shell as environment variables rather than
  being expanded into the script, so that nothing from a pull request runs as shell code.

- **`permissions: contents: read`**: The job only reads the repository, as `ci.yml` does. Labels come
  from the event payload, so reading them needs no extra permission.

## Risks / Trade-offs

- [Every change shows a failed check during review] → This is the intended signal, and it's separate
  from `test`. The check's output says to archive or add the label.
- [The label is forgotten after its use, and stays on a pull request that no longer needs it] → It
  only applies to that pull request, and the exception still needs a follow-up archive.
- [A later pull request that edits an active change on `main` fails] → That's correct: it's unfinished
  work. Archive the change in that pull request, or add the label.
- [The check's name must exist before the ruleset can require it] → Add it after the first run, while
  this pull request is open.
- [A broken workflow blocks every merge, with no bypass] → The workflow is small and verified on its
  own pull request. An admin can remove the check from the ruleset if it's ever what's broken.

## Migration Plan

1. Open the pull request, which runs `archive-check` for the first time. It fails, because this change
   is active.
2. Add `archive-check` to the required status checks in the `main` ruleset.
3. Verify the label scenarios on the pull request.
4. Finish review, archive this change on the branch, and confirm that both checks pass.

To roll back, remove `archive-check` from the ruleset first, then revert the pull request.
