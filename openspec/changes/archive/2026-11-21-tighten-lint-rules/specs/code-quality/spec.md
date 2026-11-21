## MODIFIED Requirements

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
