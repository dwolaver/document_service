# Spec Delta

## MODIFIED Requirements

### Requirement: Configure the model and retrieval

The service SHALL read the model name, Ollama address, context window size, request timeout, answer
length limit, retrieval limit and index path from a version-controlled configuration. When the
`OLLAMA_BASE_URL` environment variable is set and not empty, its value SHALL replace the Ollama
address from the configuration. It SHALL fail before calling the model when a value is missing or
invalid.

#### Scenario: Different model

- **WHEN** the configuration names another installed model
- **THEN** answers come from that model with no code change

#### Scenario: Invalid configuration

- **WHEN** a configuration value is missing, has the wrong type, or is not positive where it must be
- **THEN** the response is a failure with the configuration error code, naming the value

#### Scenario: Ollama address from the environment

- **WHEN** `OLLAMA_BASE_URL` is set to `http://ollama:11434`
- **THEN** requests go to `http://ollama:11434`, whatever the configuration's `llm.base_url` says

#### Scenario: Ollama address from the configuration

- **WHEN** `OLLAMA_BASE_URL` is unset or empty
- **THEN** requests go to the configuration's `llm.base_url`
