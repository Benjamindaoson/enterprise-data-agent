## ADDED Requirements

### Requirement: Project has repeatable classroom setup
The system SHALL provide repeatable setup steps for running backend, frontend, and seeded demo data.

#### Scenario: Fresh setup
- **WHEN** an instructor follows the documented setup from a clean checkout
- **THEN** the backend and frontend SHALL start with demo data available

### Requirement: Demo question set verifies the MVP
The system SHALL include a list of classroom demo questions covering every first-version capability.

#### Scenario: Demo questions cover capabilities
- **WHEN** the instructor reviews the demo question set
- **THEN** it SHALL include questions for sales metrics, ad analysis, refund analysis, review insight, listing optimization, chart generation, and anomalies

### Requirement: Verification checks are runnable
The project SHALL define minimal runnable verification checks for backend and frontend.

#### Scenario: Backend verification
- **WHEN** backend verification is run
- **THEN** it SHALL validate application startup and representative service/tool behavior

#### Scenario: Frontend verification
- **WHEN** frontend verification is run
- **THEN** it SHALL validate that the frontend builds successfully
