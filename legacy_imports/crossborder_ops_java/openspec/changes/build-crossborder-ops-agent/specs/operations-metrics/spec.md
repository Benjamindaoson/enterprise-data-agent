## ADDED Requirements

### Requirement: Store and SKU metrics are deterministic
The system SHALL calculate store, SKU, order, profit, refund, review, and advertising metrics in Java services backed by database queries.

#### Scenario: Sales and profit summary
- **WHEN** a user asks for sales and profit over a date range
- **THEN** the system SHALL return totals calculated from stored order records

#### Scenario: Refund rate ranking
- **WHEN** a user asks for highest refund-rate SKUs
- **THEN** the system SHALL rank SKUs using refund records and order counts for the requested period

#### Scenario: Advertising ACOS alert
- **WHEN** a user asks for high-ACOS campaigns
- **THEN** the system SHALL identify campaigns whose advertising cost of sales exceeds the configured threshold

### Requirement: Metrics support classroom seed data
The system SHALL include seed data that demonstrates normal trends and at least one operational anomaly.

#### Scenario: Demo anomaly exists
- **WHEN** the demo database is initialized
- **THEN** at least one SKU, store, or ad campaign SHALL produce an anomaly result for the prepared demo questions
