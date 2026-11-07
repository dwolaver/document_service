# Tasks

## 1. Declared test dependencies

- [x] 1.1 Add `requirements-dev.txt` containing `-r requirements.txt` and `pytest==9.2.0`; verify that installing it into a new, empty virtual environment on Python 3.14 and running `python -m pytest` gives 23 passed and 1 skipped

## 2. CI workflow

- [x] 2.1 Add `.github/workflows/ci.yml` with one job named `test`, triggered by `pull_request` targeting `main` and `push` to `main`, with workflow-level `permissions: contents: read`, using current major-version tags of `actions/checkout` and `actions/setup-python`; the job installs Python 3.14 and `requirements-dev.txt`, then runs `python -m pytest`, and leaves `RFC_DOWNLOADER_NETWORK_TESTS` unset; verify the file parses as valid YAML and matches the triggers in the spec
- [x] 2.2 Update `README.md` to describe the CI gate and how to run the tests locally with `requirements-dev.txt` and `python -m pytest`; verify the documented commands run as written

## 3. Pull request verification

- [x] 3.1 Commit to the `add-basic-ci` branch and open a pull request against `main`; verify the `test` check runs automatically and passes, with 23 passed and 1 skipped in its log
- [x] 3.2 Add `test` to the required status checks in the `main` ruleset (manual repository setting); verify `gh api repos/dwolaver/document_service/rules/branches/main` lists the `test` check
- [x] 3.3 Push a temporary failing test to the pull request; verify the `test` check fails, GitHub reports the pull request as not mergeable, and then revert the commit and confirm the check passes again
- [ ] 3.4 Squash merge the pull request; verify the `test` check runs on the resulting commit on `main` and passes

## Workflow follow-up

- Archive the change after the pull request is merged, through a follow-up branch and pull request, because `main` no longer accepts direct pushes.
- Update the README roadmap to mark step [0] complete as part of that follow-up.
