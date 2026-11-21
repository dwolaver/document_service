# code-quality Specification

## Purpose

Keeps the project's Python code consistently formatted, free of common lint errors and type-checked,
so that problems a tool can find are caught before review rather than by a test that happens to reach
them.

## Requirements

### Requirement: Lint the code

The project's Python code in the package, the tests and the release scripts SHALL pass the project's
lint rules, which SHALL be defined in the project's version-controlled configuration. The rules SHALL
check for: the linter's default errors; import order; common bug patterns; syntax that the project's
minimum Python version makes outdated, such as formatting an f-string can replace; logging calls,
such as a message formatted before it's passed to the logger; lines longer than the line-length
limit; code a simpler construct can replace; the linter's own checks, such as a test pattern with
unescaped metacharacters; and the test framework's conventions, such as one condition per assertion.

#### Scenario: Unused import

- **WHEN** a module imports a name it never uses
- **THEN** the lint check reports the file and line, and fails

#### Scenario: Formatting that an f-string can replace

- **WHEN** a module builds a string with `str.format()` or `%` formatting on a string literal, where an f-string would give the same result
- **THEN** the lint check reports the file and line, and fails

#### Scenario: Log message formatted in advance

- **WHEN** a module passes a logger a message built with an f-string, `str.format()` or `%`, or logs through the root logger
- **THEN** the lint check reports the file and line, and fails

#### Scenario: Line over the length limit

- **WHEN** a line, including a string or a comment the formatter can't wrap, is longer than the line-length limit
- **THEN** the lint check reports the file and line, and fails

#### Scenario: Simpler construct available

- **WHEN** a module opens a file without a context manager, or builds a list in a loop that a comprehension could build
- **THEN** the lint check reports the file and line, and fails

#### Scenario: Unescaped test pattern

- **WHEN** a test passes `pytest.raises` a `match` pattern with regex metacharacters, in a string that isn't raw
- **THEN** the lint check reports the file and line, and fails

#### Scenario: Combined test assertion

- **WHEN** a test asserts two conditions in one `assert` joined by `and`
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
configuration. Every function in the package and the release scripts SHALL be fully annotated and
SHALL pass the type checker's strict mode. Test code SHALL be type-checked inside function bodies,
without requiring test functions and fixtures to be annotated. A suppressed type-check error SHALL
name the error code it suppresses, and a suppression that is no longer needed SHALL fail the check.

#### Scenario: Wrong argument type

- **WHEN** an annotated function is called with an argument of a type its annotation doesn't allow
- **THEN** the type check reports the call and fails

#### Scenario: Unannotated code

- **WHEN** a function in the package or the release scripts has no annotations, or only some
- **THEN** the type check reports the function and fails

#### Scenario: Unannotated test

- **WHEN** a test function or fixture has no annotations
- **THEN** the type check doesn't report the missing annotations, and still reports a type error in its body, such as calling a method that doesn't exist on a value of a known type

#### Scenario: Suppression without an error code

- **WHEN** a line suppresses type-check errors without naming the error code
- **THEN** the type check reports the line and fails

#### Scenario: Unneeded suppression

- **WHEN** a line suppresses a type-check error that the line doesn't have
- **THEN** the type check reports the line and fails

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
