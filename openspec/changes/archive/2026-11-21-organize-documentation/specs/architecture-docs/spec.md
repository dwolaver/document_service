## MODIFIED Requirements

### Requirement: Organize the file from overview to detail

The file SHALL present, in order, the high-level architecture, the workflows with Mermaid diagrams,
the public interfaces, the internal interfaces, and the key decisions. A link back to the README
SHALL appear below the title, before the first section. The file SHALL describe only what the code
implements, leaving planned work to the roadmap in `docs/roadmap.md`.

#### Scenario: Section order

- **WHEN** the file is generated
- **THEN** its sections appear in the order above, and each workflow section includes a Mermaid diagram

#### Scenario: Link back to the README

- **WHEN** the file is generated or updated
- **THEN** a link to the README appears below the title

#### Scenario: Planned work

- **WHEN** a roadmap step isn't implemented in the code
- **THEN** the file doesn't describe it as existing
