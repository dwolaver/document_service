# code-quality Specification

## Purpose

Keeps the project's Python code consistently formatted, free of common lint errors and type-checked,
so that problems a tool can find are caught before review rather than by a test that happens to reach
them.

## Requirements

### Requirement: Lint the code

The project's Python code in the package, the tests and the release scripts SHALL pass the project's
lint rules. The rules SHALL include the linter's default error checks, import sorting and common bug
patterns, and SHALL be defined in the project's version-controlled configuration.

#### Scenario: Unused import

- **WHEN** a module imports a name it never uses
- **THEN** the lint check reports the file and line, and fails

#### Scenario: Clean code

- **WHEN** the code has no lint findings
- **THEN** the lint check passes

### Requirement: Format the code consistently

The project's Python code SHALL match the output of the project's formatter, with lines of up to 110
characters. The format check SHALL report a file that would change without changing it.

#### Scenario: Unformatted file

- **WHEN** a file's layout differs from what the formatter would produce
- **THEN** the format check names the file and fails, and the file is left unchanged

#### Scenario: Formatted code

- **WHEN** every file matches the formatter's output
- **THEN** the format check passes

### Requirement: Type-check the code

The project's Python code SHALL pass the type checker at the strictness set in the project's
configuration. Functions with no annotations MAY be left unchecked until a later change makes the
checking stricter.

#### Scenario: Wrong argument type

- **WHEN** an annotated function is called with an argument of a type its annotation doesn't allow
- **THEN** the type check reports the call and fails

#### Scenario: Unannotated code

- **WHEN** a function has no annotations
- **THEN** the type check doesn't report errors inside it

### Requirement: Use one pinned version of each tool

The linter, formatter, type checker and hook runner SHALL be pinned to exact versions in the
project's development dependencies. The pre-commit hook and the automated checks SHALL both use those
versions, so that a check that passes locally passes in the automated checks too.

#### Scenario: Same result locally and in the automated checks

- **WHEN** the code quality checks pass on a developer's machine with the development dependencies installed
- **THEN** they pass in the automated checks for the same commit

### Requirement: Run the checks before each commit

The project SHALL provide a pre-commit hook configuration that runs the lint, format and type checks
before each commit, once a developer has installed the hook. A commit SHALL be stopped when any check
fails.

#### Scenario: Commit with a lint finding

- **WHEN** a developer with the hook installed commits a change that has a lint finding
- **THEN** the commit is stopped and the finding is reported

#### Scenario: Commit that passes

- **WHEN** a developer with the hook installed commits a change that passes every check
- **THEN** the commit is created
