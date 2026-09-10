## ADDED Requirements

### Requirement: Chat agent routes business questions to tools
The system SHALL provide a cross-border operations chat agent that interprets user questions and calls approved Java tools for business data.

#### Scenario: Tool-backed business answer
- **WHEN** a user asks for store sales, ad performance, refund, review, or listing help
- **THEN** the agent MUST use a registered business tool instead of inventing unsupported data

#### Scenario: Out-of-scope question
- **WHEN** a user asks for a capability outside the MVP scope
- **THEN** the agent SHALL explain the limitation and suggest supported analysis options

### Requirement: Streaming chat remains available
The system SHALL support streaming agent responses for the frontend chat experience.

#### Scenario: Streaming response completes
- **WHEN** the frontend sends a message to the streaming chat endpoint
- **THEN** the backend SHALL emit token events and a completion event

### Requirement: Chat memory persists by session
The system SHALL maintain bounded conversation memory per session.

#### Scenario: Session memory reused
- **WHEN** a user continues a previous session
- **THEN** the agent SHALL receive recent session context without mixing messages from other sessions
