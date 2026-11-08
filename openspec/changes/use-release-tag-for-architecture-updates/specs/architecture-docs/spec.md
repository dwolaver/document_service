# Spec Delta

## MODIFIED Requirements

### Requirement: Update the file from the recorded commit

When `ARCHITECTURE.md` exists and was produced by the pinned model, the generator SHALL use the
changes since a starting point to find the sections to revise. The starting point SHALL be the tag of
the release named in the generation line when that tag exists, otherwise the commit recorded in the
generation line when that commit is available. It SHALL then check every file, function, parameter
and diagram step the file names against the current code, and correct any that are wrong, including
in sections the changes didn't touch.

#### Scenario: Code changed since the last update

- **WHEN** the generator runs after code changes since the starting point
- **THEN** the affected sections are revised to match the code

#### Scenario: Stale claim outside the changed area

- **WHEN** the file names a function that no longer exists, in a section the recent changes didn't touch
- **THEN** the generator corrects that section too

#### Scenario: Release tag exists

- **WHEN** the generation line names release v0.1.0 and the tag `v0.1.0` exists
- **THEN** the changes are taken from `v0.1.0` to `HEAD`, even if the recorded commit is also available

#### Scenario: Only the recorded commit exists

- **WHEN** the release named in the generation line has no tag, and the recorded commit is available
- **THEN** the changes are taken from the recorded commit to `HEAD`

#### Scenario: Neither starting point exists

- **WHEN** the release has no tag and the recorded commit isn't available, for example after a squash merge and branch deletion
- **THEN** the generator checks every section against the code, keeps the key decisions under the usual rules, and reports that no starting point was found

#### Scenario: Starting point reported

- **WHEN** an update finishes
- **THEN** the report names the starting point it used, or says that none was available
