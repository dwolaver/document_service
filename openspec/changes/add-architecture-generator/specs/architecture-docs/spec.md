# Spec Delta

## Purpose

Keeps an `ARCHITECTURE.md` that describes the system as the source code shows it, produced only by a
pinned model, with key decisions whose assumptions are reviewed at each release.

## ADDED Requirements

### Requirement: Generate the file from the source code

When `ARCHITECTURE.md` doesn't exist, the generator SHALL create it from the source code. The source
code SHALL be the source of truth for everything the file says exists. Archived OpenSpec designs MAY
supply the reasons for key decisions, but not facts about the current code.

#### Scenario: No file yet

- **WHEN** the generator runs and `ARCHITECTURE.md` doesn't exist
- **THEN** it writes a complete file from the source code

#### Scenario: Design and code disagree

- **WHEN** an archived design describes something the code no longer does
- **THEN** the file follows the code

### Requirement: Update the file from the recorded commit

When `ARCHITECTURE.md` exists and was produced by the pinned model, the generator SHALL use the
changes since the commit recorded in its header to find the sections to revise. It SHALL then check
every file, function, parameter and diagram step the file names against the current code, and
correct any that are wrong, including in sections the changes didn't touch.

#### Scenario: Code changed since the last update

- **WHEN** the generator runs after code changes since the recorded commit
- **THEN** the affected sections are revised to match the code

#### Scenario: Stale claim outside the changed area

- **WHEN** the file names a function that no longer exists, in a section the recent changes didn't touch
- **THEN** the generator corrects that section too

### Requirement: Record what produced the file

Directly under its title, the file SHALL have a line giving the commit it was generated from, the
full ID of the model that generated it, and the release it was generated for.

#### Scenario: Header after a run

- **WHEN** the generator runs at commit `3b64fbc` with `claude-opus-5-5` for v0.1.0
- **THEN** the header reads `Generated from commit 3b64fbc by claude-opus-5-5, for release v0.1.0.`

### Requirement: Organize the file from overview to detail

The file SHALL present, in order, the high-level architecture, the workflows with Mermaid diagrams,
the public interfaces, the internal interfaces, and the key decisions. It SHALL describe only what the
code implements, leaving planned work to the README's roadmap.

#### Scenario: Section order

- **WHEN** the file is generated
- **THEN** its sections appear in the order above, and each workflow section includes a Mermaid diagram

#### Scenario: Planned work

- **WHEN** a roadmap step isn't implemented in the code
- **THEN** the file doesn't describe it as existing

### Requirement: Separate public and internal interfaces

Public interfaces SHALL include what outside users and callers rely on, such as the query API, the
command lines and the configuration files. Internal interfaces SHALL include the functions and types
without a leading underscore that connect modules. Names with a leading underscore SHALL be left out.

#### Scenario: Private helper

- **WHEN** a module has a function whose name starts with an underscore
- **THEN** the file doesn't document it

### Requirement: Keep reviewed key decisions

The key decisions section SHALL give each decision its reason, the assumption that would change it,
its status, the release it was last reviewed at, and its source. The generator MAY add a decision
with status `New`, or set an existing decision to `Review needed` with a reason. Only the repository
owner SHALL set a decision to `Current` or change when it was last reviewed. Each run SHALL list the
assumptions it can't check from the code.

#### Scenario: Assumption touched by a release

- **WHEN** code changes affect what a `Current` decision assumes
- **THEN** the generator sets it to `Review needed`, with the reason, and leaves `Last reviewed` unchanged

#### Scenario: New decision

- **WHEN** the generator records a decision that isn't in the section yet
- **THEN** it has status `New` and no `Last reviewed` value

#### Scenario: Assumption outside the code

- **WHEN** a decision rests on something outside the code, such as a library's features
- **THEN** the run lists it as a question for the owner, without changing its status

### Requirement: Preserve key decisions across regeneration

Regenerating the file SHALL keep the existing key decisions, including their review notes and any
`Superseded` rows. A decision overturned by review SHALL stay in the section as `Superseded`, with a
link to the change that replaced it.

#### Scenario: Full regeneration

- **WHEN** the rest of the file is regenerated from scratch
- **THEN** every existing key decision row is carried over, with only status changes this requirement and the previous one allow

### Requirement: Pin the model by its full ID

The skill SHALL name the model by its full ID, not an alias, and that SHALL be the only place the
model is set. The skill SHALL stop at its first step when it isn't running as that model.

#### Scenario: Alias in the skill

- **WHEN** the skill's model is an alias such as `opus`
- **THEN** the script refuses to run and says a full model ID is required

### Requirement: Accept only results from the pinned model

The script SHALL run the skill headlessly and keep the result only when the run succeeded and the
pinned model did the main work. Otherwise it SHALL restore `ARCHITECTURE.md` to its state before the
run, report why, and exit with a non-zero status.

#### Scenario: Pinned model did the work

- **WHEN** the run succeeds and the pinned model produced more output than any other model it used
- **THEN** the new `ARCHITECTURE.md` is kept for review

#### Scenario: Small helper model

- **WHEN** a small helper model also appears in the run, with less output than the pinned model
- **THEN** the result is accepted

#### Scenario: Another model did the work

- **WHEN** the pinned model is missing from the run, or another model produced more output
- **THEN** the result is rejected, the file is restored, and the report names the models and their output

#### Scenario: Run fails

- **WHEN** the run exits with an error or reports an error result, such as an unavailable model
- **THEN** the result is rejected and the file is restored

#### Scenario: File didn't exist before

- **WHEN** a rejected run had created `ARCHITECTURE.md` where none existed
- **THEN** the file is removed

### Requirement: Protect work outside the run

The script SHALL refuse to start when `ARCHITECTURE.md` has uncommitted changes. When a run changes
any other file, the script SHALL reject the result and list those files, without changing them.

#### Scenario: Uncommitted edits

- **WHEN** `ARCHITECTURE.md` has uncommitted changes
- **THEN** the script exits with a non-zero status before running anything

#### Scenario: Other file changed

- **WHEN** a run modifies a file other than `ARCHITECTURE.md`
- **THEN** the result is rejected and the changed files are listed

### Requirement: Validate a model switch more thoroughly

When the model recorded in the file's header differs from the pinned model, the generator SHALL
regenerate every section except the key decisions, rather than following the changes, and SHALL list
what changed in meaning for the owner to review.

#### Scenario: Pinned model changed

- **WHEN** the header names a different model from the one the skill pins
- **THEN** the file is regenerated apart from key decisions, and the run lists the changes in meaning

### Requirement: Explain why the script exists

The script SHALL state in its comments why it enforces the model instead of the skill, link the Claude
Code documentation on skill models, and state that it can be removed in favor of the skill alone once
a skill can refuse to run on a model mismatch.

#### Scenario: Reading the script

- **WHEN** someone opens the script
- **THEN** its opening comment gives the rationale, the documentation link and the condition for removing it
