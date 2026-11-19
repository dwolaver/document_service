# Spec Delta

## MODIFIED Requirements

### Requirement: Verify the test suite from a clean environment

The automated checks SHALL install the project and only its declared dependencies into a clean
environment on the project's supported Python version, then run the test suite. The checks
SHALL fail when the project can't be installed, when any test fails or when the tests cannot be
collected or run.

#### Scenario: All tests pass

- **WHEN** the test suite passes on the proposed change
- **THEN** the automated checks report success

#### Scenario: A test fails

- **WHEN** any test in the suite fails
- **THEN** the automated checks report failure

#### Scenario: Undeclared dependency

- **WHEN** the test suite needs a package that the project does not declare
- **THEN** the automated checks report failure

#### Scenario: Project can't be installed

- **WHEN** the project's package definition is invalid or names a command whose target doesn't exist
- **THEN** the automated checks report failure
