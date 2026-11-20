# Spec Delta

## ADDED Requirements

### Requirement: Scan pull request commits for secrets

The automated checks SHALL scan every commit a pull request adds, and every commit pushed to `main`,
for secrets, with the same scanner version as the pre-commit hook. They SHALL report the result as a
check separate from the test suite and the code quality checks, and SHALL fail when any of those
commits contains a secret. Changes SHALL NOT merge to `main` unless this check has passed.

#### Scenario: Secret added and then removed in a pull request

- **WHEN** one commit of a pull request adds a secret and a later commit of the same pull request deletes it
- **THEN** the secret scan fails and names the commit that added it

#### Scenario: Hook skipped locally

- **WHEN** a commit containing a secret is pushed to a pull request, after the developer skipped or never installed the pre-commit hook
- **THEN** the secret scan fails on the pull request, and the pull request can't merge

#### Scenario: Pull request without secrets

- **WHEN** no commit in a pull request contains a secret
- **THEN** the secret scan passes
