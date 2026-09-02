from eiw.persistence.tables import metadata


def test_persistence_has_single_authoritative_contract_tables() -> None:
    required = {
        "analysis_task",
        "task_state",
        "runtime_checkpoint",
        "analysis_context",
        "analysis_plan",
        "analysis_step",
        "hypothesis",
        "execution_record",
        "observation",
        "validation_result",
        "claim",
        "evidence",
        "claim_evidence_link",
        "artifact",
        "domain_event",
        "audit_event",
        "evaluation_case",
        "evaluation_run",
        "evaluation_result",
    }
    assert required <= set(metadata.tables)
