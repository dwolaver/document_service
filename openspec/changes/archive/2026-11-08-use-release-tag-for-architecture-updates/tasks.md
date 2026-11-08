# Tasks

## 1. Skill

- [x] 1.1 Update step 2 of `.claude/skills/update-architecture/SKILL.md` to choose the starting point: resolve the release tag from the generation line with `git rev-parse --verify --quiet`, fall back to the recorded commit, and use a full check when neither resolves; verify each spec scenario has a matching instruction, and that the commands are within the script's allowed tools
- [x] 1.2 Update the rest of the skill to match: the `git diff` and `git log` commands use the chosen starting point, the key decisions rule refers to changes since the starting point, and the report names the starting point or says none was found; verify no instruction still assumes the recorded commit

## 2. Verification in throwaway clones

- [x] 2.1 Clone `main` with a single branch into the scratch directory, confirm `v0.1.0` resolves and `72f98af` doesn't, and run `python scripts/update_architecture.py v0.1.0` there; verify the run is accepted and the report names `v0.1.0` as the starting point
- [x] 2.2 In a second clone, delete the `v0.1.0` tag locally, run the script again, and verify the run is accepted, the report says no starting point was found, and the key decisions are unchanged
- [x] 2.3 Confirm this repository's `ARCHITECTURE.md` is unchanged by the tests, and delete the clones

## Workflow follow-up

- Open a pull request from `use-release-tag-for-architecture-updates`. The `test` check must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the change. Any changes are made on this branch, in the active change, and `test` must pass again.
- Archive the change on this branch as the last step, which makes the change complete and turns `archive-check` green.
- The repository owner squash merges once both checks pass, so that the skill, spec and archive land as one commit on `main`.
- After the merge, the `add-architecture-generator` branch can be deleted.
