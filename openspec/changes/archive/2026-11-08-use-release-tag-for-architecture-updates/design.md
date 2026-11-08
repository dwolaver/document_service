# Design

## Context

See proposal.md - Why. Requirements are in specs/architecture-docs/spec.md.

The skill reads the generation line at the end of `ARCHITECTURE.md`, for example
`Generated from commit 72f98af by claude-opus-5-5, for release v0.1.0.`, and runs
`git diff --stat <commit>..HEAD` and `git log --oneline <commit>..HEAD` from the recorded commit.
`add-architecture-generator` rejected tags as a starting point only because the repository had none.

After v0.1.0 was tagged, checks showed:

- `v0.1.0` points at `d40169b`, the tip of `main` and PR #8's squash commit, and its tree holds the
  reviewed `ARCHITECTURE.md`.
- None of the branch commits `a7fc62b`, `d0517bb` and `72f98af` is in `main`'s history. They're still
  available only because the `add-architecture-generator` branch exists.
- `git rev-parse --verify --quiet '<ref>^{commit}'` prints the commit for a tag or commit that exists,
  and exits 1 with no output for one that doesn't. `git rev-parse` is already one of the script's
  allowed tools.

## Goals / Non-Goals

**Goals:**
- An update that works after every squash merge and branch deletion.
- A defined result when no starting point can be found, instead of a failed command.

**Non-Goals:**
- Changing the generation line's format, or the script.
- Making releases depend on annotated tags. Lightweight tags work the same way here.

## Decisions

- **Try the release tag first, then the recorded commit**: A tag is permanent, sits on `main`, and
  points at the file as it was reviewed and merged. The recorded commit only works until its branch
  is gone. Keeping it as a fallback covers a release that was never tagged.

- **Check with `git rev-parse --verify --quiet`**: It needs no new tool permissions, and it works for
  both tags and commits. The skill resolves `<release>^{commit}`, then `<commit>^{commit}`, and uses
  the first one that resolves.

- **No starting point means a full check, not a model switch**: The file's model hasn't changed, so the
  stricter model-switch path, which ignores the old text, would be excessive. The skill checks every
  section against the code, as it already does at the end of every update, and keeps the key decisions
  under the usual rules. Its report says no starting point was found, so the owner knows the review
  needs more care. Treating this as an error was rejected, because the file can still be brought up to
  date accurately.

- **Report the starting point**: The report names the tag or commit used, or says none was available.
  The owner can then see how much the update relied on the diff.

- **Keep the generation line as it is**: The recorded commit still helps when a release isn't tagged,
  and the current file stays valid with no migration. Dropping the commit from the line was considered
  and rejected, because it would change the spec's format for no practical gain.

- **Test in a throwaway clone**: A single-branch clone of `main` has the tag but not the branch commits,
  which is exactly the situation after branch deletion. Deleting the tag in a second clone tests the
  no-starting-point path. Neither test changes this repository's `ARCHITECTURE.md`, which should only
  be regenerated for a release.

## Risks / Trade-offs

- [A tag is moved or deleted after release] → The skill falls back to the commit, then to a full
  check, and reports which one it used.
- [The release in the generation line doesn't match a tag name, such as a typo] → Same fallback. The
  report shows that the tag wasn't found.
- [The full check misses something the diff would have shown] → It covers every section, which is
  what the final verification already does on every run.
- [Testing costs Opus usage] → Two update runs in clones, each about a minute based on earlier
  updates.

## Migration Plan

No migration. The current `ARCHITECTURE.md` already names release v0.1.0, which is tagged, so the next
update starts from `v0.1.0`. After this merges, the `add-architecture-generator` branch can be deleted.
