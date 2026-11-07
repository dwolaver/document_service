# Spec Delta

## ADDED Requirements

### Requirement: Require changes to be archived before merge

A required check SHALL run on every pull request targeting `main`, separately from the test suite.
It SHALL fail when the pull request adds or modifies a file in an active OpenSpec change, and pass
otherwise. Files under the archive, and deletions from active changes, SHALL NOT count.

#### Scenario: Active change in a pull request

- **WHEN** a pull request adds or modifies files in `openspec/changes/<name>/`
- **THEN** the check fails and names the files, and the pull request cannot be merged

#### Scenario: Change archived on the branch

- **WHEN** a change on the branch is moved to `openspec/changes/archive/`
- **THEN** the check passes for that change, and the pull request can be merged if the other required checks pass

#### Scenario: Archive-only pull request

- **WHEN** a pull request only moves an already merged change into the archive
- **THEN** the check passes

#### Scenario: Pull request with no OpenSpec change

- **WHEN** a pull request changes nothing under `openspec/changes/`
- **THEN** the check passes

#### Scenario: Unrelated active change on main

- **WHEN** `main` already holds an active change that a pull request does not touch
- **THEN** the check passes for that pull request

#### Scenario: Result is separate from the tests

- **WHEN** the check fails on a pull request whose tests pass
- **THEN** the test check still reports success

### Requirement: Allow a labeled exception

A pull request with the `merge-before-archive` label SHALL pass the archive check, for changes with
work that can only happen after merge. Adding or removing the label SHALL update the check's result
without a new commit. The label SHALL NOT affect any other required check.

#### Scenario: Label added

- **WHEN** the `merge-before-archive` label is added to a pull request with an active change
- **THEN** the archive check runs again and passes

#### Scenario: Label removed

- **WHEN** the label is removed from a pull request with an active change
- **THEN** the archive check runs again and fails

#### Scenario: Tests fail with the label

- **WHEN** a pull request has the label and its tests fail
- **THEN** the pull request cannot be merged
