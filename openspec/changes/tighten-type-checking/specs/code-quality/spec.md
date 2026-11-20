# Spec Delta

## MODIFIED Requirements

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
