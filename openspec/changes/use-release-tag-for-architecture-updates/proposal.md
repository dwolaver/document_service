# Proposal

## Why

`ARCHITECTURE.md` is generated on a release branch, and its generation line records that branch's
commit. Squash merging means that commit never reaches `main`. For v0.1.0 the line records
`72f98af`, which `main` doesn't contain. Once the branch is deleted and the commit is cleaned up, the
next update's `git diff 72f98af..HEAD` will fail, and the skill has no instruction for that case.
Every future release would repeat the problem.

The release tag is a better starting point. `v0.1.0` is on `main` and points at the commit that
contains the reviewed file. The original design rejected tags only because none existed yet.

## What Changes

- The skill starts an update from the tag of the release named in the generation line, when that tag
  exists.
- When the tag doesn't exist, it falls back to the recorded commit, if that commit is available.
- When neither is available, it checks every section against the code, as if no changes were known,
  keeps the key decisions, and says so in its report.
- The report names the starting point it used.
- The generation line keeps its format, so the current `ARCHITECTURE.md` stays valid.

Out of scope: changing the enforcement script, which already allows the git commands this needs, and
regenerating `ARCHITECTURE.md`, which waits for the next release.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `architecture-docs`: Updates start from the previous release's tag, with defined fallbacks when the
  tag or the recorded commit isn't available.

## Impact

- Updated: `.claude/skills/update-architecture/SKILL.md`, and the architecture-docs spec.
- `ARCHITECTURE.md` describes the regeneration workflow, so the next release run will pick up the new
  starting point.
- No code or dependency changes. `git rev-parse` is already among the script's allowed tools.
- Until this merges, the `add-architecture-generator` branch should be kept, so that `72f98af` stays
  available.
