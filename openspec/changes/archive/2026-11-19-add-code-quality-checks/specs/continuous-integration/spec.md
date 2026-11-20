# Spec Delta

## ADDED Requirements

### Requirement: Run the code quality checks

The automated checks SHALL run the project's lint, format and type checks on every Python file in the
repository, using the same hook configuration and tool versions as the pre-commit hook. They SHALL
report the result as a check separate from the test suite, and SHALL fail when any of the code quality
checks fails. Changes SHALL NOT merge to `main` unless this check has passed.

#### Scenario: Hook skipped locally

- **WHEN** a commit that fails the format check is pushed to a pull request, after the developer skipped or never installed the pre-commit hook
- **THEN** the code quality check fails on the pull request, and the pull request can't merge

#### Scenario: Clean pull request

- **WHEN** every Python file passes the lint, format and type checks
- **THEN** the code quality check passes

#### Scenario: Reported separately from the tests

- **WHEN** the code quality check fails and the test suite passes
- **THEN** the pull request shows the code quality check as failed and the test check as passed
