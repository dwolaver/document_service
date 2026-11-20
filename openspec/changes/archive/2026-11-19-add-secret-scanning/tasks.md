# Tasks

## 1. Hook and history scan

- [x] 1.1 Add the `gitleaks` hook from `https://github.com/gitleaks/gitleaks` at `rev: v8.30.1` to `.pre-commit-config.yaml`, and update the file's header comment, which says every version is pinned in `requirements-dev.txt`; verify `pre-commit run gitleaks` builds the hook without a separately installed gitleaks or Go, and passes with nothing staged
- [x] 1.2 Scan all of the repository's history once with the hook's gitleaks binary (`gitleaks git --redact --verbose` from the pre-commit cache); verify it reports no findings, or stop and report each finding (file, line, commit and rule, value redacted) for review before continuing: record a reviewed false positive's fingerprint in `.gitleaksignore`, and leave a real secret for the repository owner to decide
- [x] 1.3 In a throwaway clone with the hook installed, verify that staging a file with a fake credential (for example a generated, unused private key) stops the commit with a report naming the file and line and not showing the value, that a commit without secrets goes through, and, if `.gitleaksignore` was created, that an ignored fingerprint isn't reported while another finding in the same file still is

## 2. CI

- [x] 2.1 Add a `secrets` job to `.github/workflows/ci.yml` as in design.md: full-history checkout, the gitleaks version read from the hook's `rev`, the release archive checked against its published checksums, and `gitleaks git --redact --verbose` over the pull request's commits (`base..head`) or the pushed commits on `main` (all history when `before` is all zeros); set `SKIP: gitleaks` on the `quality` job's run step; verify the workflow loads with `yaml.safe_load`, and run the job's script locally with the pull request's range set to a scratch branch whose first commit adds a fake credential and whose second deletes it, checking it fails and names the first commit with the value redacted, and passes on a range without secrets; check that the version step fails when the `rev` line is missing
- [x] 2.2 Document the secret scan in the README's "Development" section: the gitleaks hook and its one-time build, the `secrets` check, that a real secret found after it was committed must be rotated as well as removed, and how to record a reviewed false positive in `.gitleaksignore`; update the sentence about which checks GitHub Actions runs; verify `pre-commit run --all-files` still passes and the README's commands work as written

## Workflow follow-up

- Open a pull request from `add-secret-scanning`. The `test`, `quality` and `secrets` checks must pass, and `archive-check` is expected to fail until the archive. Confirm `secrets` appears as its own check.
- Once `secrets` has run on the pull request, the repository owner adds it to the required checks for `main`.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and the checks must pass again.
- Archive the change on this branch as the last step, which creates the secret-scanning spec, syncs the continuous-integration spec, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
