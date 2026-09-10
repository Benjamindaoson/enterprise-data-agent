## ADDED Requirements

### Requirement: Chart data uses a structured payload contract
The system SHALL return chart data in a stable structured payload format that the frontend can parse and render.

#### Scenario: Line chart payload
- **WHEN** a user asks for a time-series trend chart
- **THEN** the response SHALL include a line chart payload with title, x-axis labels, and series values

#### Scenario: Bar chart payload
- **WHEN** a user asks for ranking or comparison
- **THEN** the response SHALL include a bar chart payload with category labels and values

#### Scenario: Invalid chart request
- **WHEN** there is no data for a chart request
- **THEN** the system SHALL return a clear no-data message rather than malformed chart JSON

### Requirement: Frontend renders supported visual payloads
The frontend SHALL detect supported visual payloads and render them with ECharts.

#### Scenario: Render chart in chat
- **WHEN** an assistant message contains a valid visual payload
- **THEN** the frontend SHALL render the chart below the assistant text
