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
