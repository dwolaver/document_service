## MODIFIED Requirements

### Requirement: Lint the code

The project's Python code in the package, the tests and the release scripts SHALL pass the project's
lint rules. The rules SHALL include the linter's default error checks, import sorting, common bug
patterns, and the checks for syntax that the project's minimum Python version makes outdated, such as
string formatting that an f-string can replace. They SHALL be defined in the project's
version-controlled configuration.

#### Scenario: Unused import

- **WHEN** a module imports a name it never uses
- **THEN** the lint check reports the file and line, and fails

#### Scenario: Formatting that an f-string can replace

- **WHEN** a module builds a string with `str.format()` or `%` formatting on a string literal, where an f-string would give the same result
- **THEN** the lint check reports the file and line, and fails

#### Scenario: Clean code

- **WHEN** the code has no lint findings
- **THEN** the lint check passes
