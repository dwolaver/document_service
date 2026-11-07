# continuous-integration Specification

## Purpose

Automatically verifies proposed and merged changes, so that `main` only accepts changes whose
tests pass and every contributor gets the same repeatable result.

## Requirements

### Requirement: Run checks on proposed and merged changes

The repository SHALL run its automated checks on every pull request that targets `main`,
including each new push to that pull request, and on every push to `main`.

#### Scenario: Pull request opened against main

- **WHEN** a pull request targeting `main` is opened
- **THEN** the automated checks run against the proposed change

#### Scenario: Pull request updated

- **WHEN** a new commit is pushed to an open pull request targeting `main`
- **THEN** the automated checks run again against the updated change

#### Scenario: Change merged to main

- **WHEN** a commit lands on `main`
- **THEN** the automated checks run against that commit

### Requirement: Verify the test suite from a clean environment

The automated checks SHALL install only the project's declared dependencies into a clean
environment on the project's supported Python version, then run the test suite. The checks
SHALL fail when any test fails or when the tests cannot be collected or run.

#### Scenario: All tests pass

- **WHEN** the test suite passes on the proposed change
- **THEN** the automated checks report success

#### Scenario: A test fails

- **WHEN** any test in the suite fails
- **THEN** the automated checks report failure

#### Scenario: Undeclared dependency

- **WHEN** the test suite needs a package that the project does not declare
- **THEN** the automated checks report failure

### Requirement: Keep checks independent of external services

The automated checks SHALL NOT depend on network access to external document sources. Tests
that require such access SHALL be skipped rather than run or failed.

#### Scenario: Network integration test in CI

- **WHEN** the automated checks run the test suite
- **THEN** tests gated behind network access are reported as skipped and do not affect the result

### Requirement: Limit the checks' repository access

The automated checks SHALL run with read-only access to repository contents.

#### Scenario: Checks run on a pull request

- **WHEN** the automated checks run
- **THEN** they can read the repository but cannot modify it

### Requirement: Block merges that fail the checks

Changes SHALL NOT merge to `main` unless they arrive through a pull request and the automated
checks have passed.

#### Scenario: Failing pull request

- **WHEN** the automated checks fail on a pull request targeting `main`
- **THEN** the pull request cannot be merged

#### Scenario: Passing pull request

- **WHEN** the automated checks pass on a pull request targeting `main`
- **THEN** the pull request can be merged

#### Scenario: Direct push to main

- **WHEN** a contributor pushes a commit directly to `main`
- **THEN** the push is rejected

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
