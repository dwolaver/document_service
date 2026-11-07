# Tasks

## 1. Label and workflow

- [x] 1.1 Create the `merge-before-archive` label in the repository, with a description of when to use it; verify `gh label list` shows it
- [x] 1.2 Add `.github/workflows/archive-check.yml` with one job named `archive-check`, triggered by `pull_request` targeting `main` on `opened`, `synchronize`, `reopened`, `labeled` and `unlabeled`, with `permissions: contents: read`, full history checkout, and values passed through `env`; verify the file parses as valid YAML, and that the same detection command run locally flags PRs #1 and #3 and passes PRs #2 and #4
- [x] 1.3 Make the failure output name the unarchived files and say how to resolve them, and pass with a clear message when the label is present; verify by running the check's script locally against the commits of PR #3 and PR #4, with and without the label value

## 2. Rule and documentation

- [x] 2.1 Update the second `tasks` rule in `openspec/config.yaml` to name the `merge-before-archive` label as the exception; verify `openspec instructions tasks` returns the updated rule
- [x] 2.2 Describe the archive check and the label in the README's Development section; verify the text matches the workflow's job and label names

## 3. Pull request verification

- [ ] 3.1 Commit to the `add-archive-gate` branch and open a pull request against `main`; verify `test` passes, and that `archive-check` runs and fails, naming this change's files
- [ ] 3.2 Add `archive-check` to the required status checks in the `main` ruleset (manual repository setting); verify `gh api repos/dwolaver/document_service/rules/branches/main` lists it, and that the pull request's merge state is `BLOCKED`
- [ ] 3.3 Add the `merge-before-archive` label to the pull request; verify `archive-check` re-runs without a new commit and passes, and that `test` is unaffected
- [ ] 3.4 Remove the label; verify `archive-check` re-runs and fails, and that the merge state returns to `BLOCKED`

## Workflow follow-up

- The repository owner reviews the code and CI runs on the pull request. Any changes are made before archive, in the active change.
- Archive the change on this branch as the last step, which makes the change complete and should turn `archive-check` green.
- The repository owner squash merges once `test` and `archive-check` both pass, so that the code, spec and archive land as one commit on `main`.
