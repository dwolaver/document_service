# documentation Specification

## Purpose

Organizes the project's documents so that the README is the entry point for every reader, each topic
has one home, the links between documents stay correct, and the changelog, security policy and
release procedure are written down.

## Requirements

### Requirement: Keep the standard documents at the root

The repository root SHALL hold `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
`ARCHITECTURE.md` and `LICENSE`. Guides to a single topic, such as configuration or the release
procedure, SHALL be Markdown files in `docs/`. Each topic SHALL be described in one document, and
other documents SHALL link to it instead of repeating it.

#### Scenario: Standard files

- **WHEN** someone opens the repository on GitHub
- **THEN** the root holds the README, changelog, contributing guide, security policy, architecture document and license

#### Scenario: Topic guide

- **WHEN** a document needs the rules for choosing the configuration or data directory
- **THEN** it links to the guide in `docs/` that describes them, instead of restating them

### Requirement: Make the README the entry point

The README SHALL say what the project is, summarize how it was built, outline the approach, give a
quick start with an example answer, show the roadmap's steps and state the license. It SHALL link to
every other document in the root and in `docs/`, each with a line saying what it covers.

#### Scenario: Every document listed

- **WHEN** a Markdown document is added at the root or in `docs/`
- **THEN** the README links to it, and the documentation test fails until it does

#### Scenario: Build story

- **WHEN** a reviewer reads the README
- **THEN** a short account of how the project was built appears before the setup instructions, with a link to the full account in `docs/`

### Requirement: Link back to the README

Every Markdown document at the root and in `docs/`, other than the README, SHALL link to the README
before its first section.

#### Scenario: Guide in docs

- **WHEN** a reader opens a guide in `docs/`
- **THEN** a link to the README appears below its title

#### Scenario: Missing back-link

- **WHEN** a document at the root or in `docs/` has no link to the README before its first section
- **THEN** the documentation test fails and names the document

### Requirement: Keep the links working

Every relative link in the Markdown documents at the root and in `docs/` SHALL point to a file or
directory that exists. A link with a fragment SHALL name a heading that exists in the target, using
GitHub's heading anchors. Links to web addresses aren't checked.

#### Scenario: Broken file link

- **WHEN** a document links to a relative path that doesn't exist
- **THEN** the documentation test fails and names the document and the link

#### Scenario: Broken anchor

- **WHEN** a document links to `usage.md#asking-a-question` and `usage.md` has no heading with that anchor
- **THEN** the documentation test fails and names the document and the link

### Requirement: Record every change in the changelog

`CHANGELOG.md` SHALL follow the Keep a Changelog format, with an `[Unreleased]` section first and a
section for each release after it, newest first. Each change SHALL add its entry under
`[Unreleased]` in the pull request that makes it, in the category that fits, such as Added, Changed
or Removed.

#### Scenario: A change merges

- **WHEN** a change's pull request merges
- **THEN** `CHANGELOG.md` on `main` has an entry for it under `[Unreleased]`

#### Scenario: Unreleased section

- **WHEN** the documentation test reads `CHANGELOG.md`
- **THEN** its first section is `[Unreleased]`, and the test fails if it isn't

### Requirement: Publish a security policy

`SECURITY.md` SHALL say which releases receive fixes, and how to report a vulnerability privately
through the repository's private vulnerability reporting, without asking for a public issue. It SHALL
say what to do when a secret reaches a commit: treat it as leaked, rotate it with whoever issued it,
and remove it from the code.

#### Scenario: Reporting a vulnerability

- **WHEN** someone finds a vulnerability
- **THEN** `SECURITY.md` tells them to report it with GitHub's private vulnerability reporting, not in a public issue

#### Scenario: Leaked secret

- **WHEN** a contributor finds that a secret was committed or pushed
- **THEN** `SECURITY.md` tells them to rotate it as well as removing it

### Requirement: Write down the release procedure

`docs/releasing.md` SHALL list the steps of a release in order: updating `ARCHITECTURE.md`, turning
`[Unreleased]` into the version's changelog section, setting the version, the pull request and its
review, and, after the merge, the tag and the GitHub release.

#### Scenario: Preparing a release

- **WHEN** the maintainer prepares a release
- **THEN** `docs/releasing.md` gives each step and the command for it, in order
