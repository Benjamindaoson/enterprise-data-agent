## ADDED Requirements

### Requirement: Role data scope is enforced in services
The system SHALL enforce operator data scope in service-layer metric queries.

#### Scenario: Operator sees assigned store only
- **WHEN** an operator asks for operational metrics
- **THEN** the service layer SHALL restrict data to the operator's assigned store

#### Scenario: Store manager sees managed stores
- **WHEN** a store manager asks for metrics
- **THEN** the service layer SHALL restrict data to stores managed by that user

#### Scenario: Operations director sees all stores
- **WHEN** an operations director asks for metrics
- **THEN** the service layer SHALL allow access to all demo stores

### Requirement: Prompt is not the security boundary
The system SHALL NOT rely on prompt instructions as the only access control mechanism.

#### Scenario: Prompt injection attempts broader access
- **WHEN** a user asks the model to ignore permissions or reveal all stores
- **THEN** the service layer SHALL still apply the user's role scope
