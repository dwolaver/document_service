# Spec Delta

## Purpose

Keeps credentials out of the repository's history, which is public, by scanning changes for secrets
before they are committed and again before they can merge.

## ADDED Requirements

### Requirement: Scan staged changes before each commit

The project's pre-commit hook configuration SHALL scan the changes being committed for secrets, once a
developer has installed the hook. A commit SHALL be stopped when the scan finds a secret. The scanner
SHALL be pinned to one release in the hook configuration, and installing the hook SHALL NOT require
installing the scanner separately.

#### Scenario: Commit containing a secret

- **WHEN** a developer with the hook installed commits a change that adds a credential, such as a private key or an API token
- **THEN** the commit is stopped, and the report names the file, the line and the kind of secret

#### Scenario: Commit without secrets

- **WHEN** a developer with the hook installed commits a change that contains no secrets
- **THEN** the secret scan passes and doesn't stop the commit

### Requirement: Redact secrets in reports

Reports of a finding SHALL NOT show the secret's value, whether locally or in the automated checks.

#### Scenario: Finding in the automated checks

- **WHEN** the automated checks find a secret
- **THEN** the log names the file, the line, the commit and the kind of secret, and the secret's value is redacted

### Requirement: Accept a reviewed false positive

A finding that has been reviewed and isn't a secret SHALL be accepted by recording its fingerprint in
a version-controlled ignore file. Only the finding with that fingerprint SHALL be ignored.

#### Scenario: Recorded false positive

- **WHEN** a finding's fingerprint is listed in the ignore file
- **THEN** the scan no longer reports that finding, and still reports any other finding in the same file
