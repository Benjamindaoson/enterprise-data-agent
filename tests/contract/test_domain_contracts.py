from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from eiw.domain.enums import ClaimType, TaskState
from eiw.domain.models import AnalysisTask, Claim, UserContext


def user_context() -> UserContext:
    return UserContext(
        user_id="analyst@example.test",
        tenant_id="demo",
        policy_version="policy-v1",
    )


def test_task_is_created_with_explicit_user_policy_context() -> None:
    task = AnalysisTask(
        user_context=user_context(),
        domain_id="iowa_liquor_wholesale",
        business_question="What happened to July wholesale sales?",
    )
    assert task.state is TaskState.CREATED
    assert task.user_context.policy_version == "policy-v1"


def test_terminal_task_requires_completion_timestamp() -> None:
    with pytest.raises(ValidationError, match="terminal task states require completed_at"):
        AnalysisTask(
            user_context=user_context(),
            domain_id="iowa_liquor_wholesale",
            business_question="What happened to July wholesale sales?",
            state=TaskState.COMPLETED,
        )


def test_verified_claim_type_is_explicit() -> None:
    claim = Claim(
        task_id=uuid4(),
        claim_type=ClaimType.FACT,
        statement="Wholesale sales changed month over month.",
        status="VERIFIED",
    )
    assert claim.claim_type is ClaimType.FACT
    assert claim.created_at.tzinfo is not None


def test_completed_task_is_valid_with_completion_timestamp() -> None:
    task = AnalysisTask(
        user_context=user_context(),
        domain_id="iowa_liquor_wholesale",
        business_question="What happened to July wholesale sales?",
        state=TaskState.COMPLETED,
        completed_at=datetime.now(UTC),
    )
    assert task.state is TaskState.COMPLETED
