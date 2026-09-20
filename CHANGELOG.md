# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-20

### Added
- **Domain E2E Tests**: 15 end-to-end tests covering Finance, Sales, and Supply Chain domains
  - Finance: revenue analysis, cost analysis, pricing analysis
  - Sales: volume trends, top vendors, regional comparison, product performance
  - Supply Chain: vendor diversity, order frequency, volume analysis, product availability
  - Cross-domain analysis and data validation tests

- **Docker Production Setup**: Multi-stage Dockerfile with non-root user, healthcheck, PostgreSQL support
- **CI/CD Pipeline**: GitHub Actions workflow with quality gates, regression testing, Docker builds
- **Availability.create_universal()**: Factory method for universal availability spanning 1900-2100
- **Semantic V2 Contract Tests**: 21 tests validating semantic layer schema and availability

### Changed
- **Data Aggregate Fix**: Fixed GROUP BY clause in data.py to resolve DuckDB binder errors
- **Test Schema Alignment**: Updated E2E tests to match actual Iowa snapshot schema (no county/city/liters columns)
- **Import Organization**: Fixed ruff import sorting in test_semantic_v2.py

### Fixed
- **Availability model_construct() Audit**: Replaced unsafe model_construct bypass with clean create_universal() factory method
- **Dataclass Field Ordering**: Fixed in analytics/period_compare.py and analytics/drilldown.py
- **SIM102/SIM103 Ruff Errors**: 20 nested if statements refactored across codebase

### Security
- Docker image runs as non-root user (eiw:eiw, uid 1000)
- Health check endpoint for container orchestration
- PostgreSQL password authentication in Docker Compose

### Infrastructure
- **pytest**: 529 tests passing
- **ruff**: 0 errors
- **mypy**: 0 errors
- **Evaluation Baseline**: baseline_v1.0.0.json with 513 passing test cases

### Documentation
- Updated README.md with current implementation status
- CI/CD workflow documentation in .github/workflows/ci.yml

## [0.2.0] - Previous

Initial release with core capabilities:
- Supervisor + Executor agent architecture
- 13 P0 analytical tools
- NL2SQL pipeline with SQLGlot parsing and security policies
- Semantic layer with 4 domain packages (Finance, Sales, Supply Chain, Iowa)
- RBAC/Governance with 22 security tests
- Python sandbox execution
- OpenTelemetry tracing
- Intent resolution
- DuckDB + Parquet reference data path
