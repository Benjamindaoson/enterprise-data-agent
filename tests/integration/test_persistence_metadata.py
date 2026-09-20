from eiw.persistence.tables import metadata


def test_persistence_has_single_authoritative_contract_tables() -> None:
    """Verify all required domain tables are defined in persistence layer."""
    required = {
        "analysis_task",
        "analysis_context",
        "analysis_plan",
        "hypothesis",
        "execution_record",
        "observation",
        "validation_result",
        "claim",
        "evidence",
        "claim_evidence",
        "artifact",
        "domain_event",
        "audit_event",
        "evaluation_case",
        "evaluation_run",
        "evaluation_result",
    }
    defined_tables = set(metadata.tables.keys())
    missing = required - defined_tables
    assert not missing, f"Missing tables: {missing}"
    assert len(defined_tables) >= len(required), "Should have at least required tables"
