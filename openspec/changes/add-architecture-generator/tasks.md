# Tasks

## 1. Skill

- [x] 1.1 Add `.claude/skills/update-architecture/SKILL.md`, pinning `claude-opus-5-5` in its `model` field, with a first step that stops if it isn't running as that model; verify the frontmatter parses and names a full model ID
- [x] 1.2 Write the skill's instructions for creating, updating and model-switch regeneration, the header line, the section order, the interface tiers, Mermaid diagrams, describing only what exists, verifying every named item against the code, and the key decisions rules; verify each requirement in the architecture-docs spec is covered by an instruction

## 2. Enforcement script

- [x] 2.1 Add `scripts/update_architecture.py` with functions that read the pinned model from `SKILL.md`, reject an alias, parse the headless JSON result, and accept a run only under the design's rule; verify unit tests cover the pinned model alone, a smaller helper model, a larger other model, a missing pinned model, `is_error` true with `subtype` success, a non-zero exit, output that isn't JSON, and an alias
- [x] 2.2 Add the run itself: refuse when `ARCHITECTURE.md` has uncommitted changes, run `claude -p` with the release and the limited tools, restore or remove the file on rejection, and reject a run that changed other files, listing them; verify unit tests with the `claude` call replaced cover acceptance, each rejection, restoring an existing file, removing a new one, and the uncommitted-changes refusal
- [x] 2.3 Write the script's opening comment with the rationale, the Claude Code documentation link, the tested behavior, and the condition for removing the script; verify it states each point the spec requires

## 3. First generation

- [x] 3.1 Run `python scripts/update_architecture.py v0.1.0` to create `ARCHITECTURE.md`; verify the run is accepted, the header matches the spec, the sections are in order with Mermaid diagrams, and key decisions are marked `New`
- [x] 3.2 Check every file, function, class and command named in `ARCHITECTURE.md` against the code, and that no underscore names or planned features appear; verify by a script that lists names not found in the code, with each one fixed or explained
- [x] 3.3 Run the script again with no code changes; verify the run is accepted, the key decisions are unchanged, and any other differences are explained
- [x] 3.4 Point `SKILL.md` at a model that isn't available, and run the script; verify it exits non-zero, reports the error, and leaves `ARCHITECTURE.md` as committed, then restore `SKILL.md`

## 4. Documentation

- [x] 4.1 Replace the README's approach section and diagram with a short summary that links to `ARCHITECTURE.md`, and add a short section on updating it before a release; verify the links work and the documented command matches the script

## Workflow follow-up

- Open a pull request from `add-architecture-generator`. The `test` check must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the code and the generated `ARCHITECTURE.md`, and sets each reviewed key decision to `Current` for v0.1.0. Any changes are made on this branch, in the active change, and `test` must pass again.
- Archive the change on this branch as the last step, which makes the change complete and turns `archive-check` green. In the same step, update the Source link in the last key decision in `ARCHITECTURE.md`, which points to this change's active design and will move to the archive.
- The repository owner squash merges once both checks pass, so that the code, spec, archive and first `ARCHITECTURE.md` land as one commit on `main`.
- Tagging v0.1.0 after the merge is part of the release, not this change, so the normal flow applies and no label is needed.
