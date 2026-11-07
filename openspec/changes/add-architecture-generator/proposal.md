# Proposal

## Why

The project has no single description of how it fits together. The specs say what it should do, the
archived designs explain individual choices, and only the code shows what exists today. An
`ARCHITECTURE.md` generated from the code just before each release gives readers one accurate
starting point, and a reviewed list of key decisions stops assumptions from quietly going stale.

This change is parked until `add-answer-generation` is finished, so that the first generated file
describes a system that answers questions.

## What Changes

- Add a Claude Code skill, `update-architecture`, that creates `ARCHITECTURE.md` from the source code
  when it's missing, and updates it based on the changes since the commit it was generated from.
- Check every claim in the file against the code on each run, using the diff only to focus the
  update.
- Pin the model in the skill by its full ID, and stop if it isn't the pinned model.
- Add `scripts/update-architecture.sh`, which runs the skill headlessly and rejects the result unless
  the pinned model did the work. Its comments explain why it exists, and that it can be removed once
  a skill can refuse to run on a model mismatch.
- Make a model switch deliberate: when the model recorded in the file differs from the pinned one,
  regenerate the whole file and list what changed in meaning, for detailed review.
- Add a "Key decisions" section with each decision's reason, the assumption to revisit, its status,
  when it was last reviewed, and its source. The generator flags possible problems, and only the
  repository owner resolves them.
- Trim the README's approach section and diagram to a link, so that there's one version to maintain.

`ARCHITECTURE.md` itself doesn't follow the OpenSpec process. The skill and script do, because they
are behavior with rules worth recording. Out of scope: running generation in CI, and supporting tools
other than Claude Code.

## Capabilities

### New Capabilities
- `architecture-docs`: Generating and updating `ARCHITECTURE.md` from the source code, enforcing the
  pinned model, and maintaining the reviewed key decisions.

### Modified Capabilities
<!-- None expected. Confirm when this change resumes. -->

## Impact

- New: `.claude/skills/update-architecture/SKILL.md`, `scripts/update-architecture.sh`, and the
  generated `ARCHITECTURE.md`.
- Updated: `README.md`.
- Requires a Claude Code installation with access to the pinned model. CI and normal development are
  unaffected.
- The `ARCHITECTURE.md` update reaches `main` through a release pull request, and `archive-check`
  passes because the file is outside `openspec/changes/`.
