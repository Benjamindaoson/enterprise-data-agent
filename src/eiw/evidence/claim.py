"""Claim Management for Enterprise Data Agent.

Claims are the conclusions drawn from analysis. They are:
- Linked to evidence
- Verified against source data
- Tracked through their lifecycle
- Subject to limitations and caveats
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ClaimStatus(Enum):
    """Lifecycle states of a claim."""

    DRAFT = "draft"           # Initial creation
    SUBMITTED = "submitted"    # Presented for verification
    VERIFIED = "verified"      # Confirmed by evidence
    QUALIFIED = "qualified"    # Verified with limitations
    REJECTED = "rejected"      # Contradicted by evidence
    SUPERSEDED = "superseded"  # Replaced by better claim


class ClaimType(Enum):
    """Types of claims."""

    FACT = "fact"              # Direct data observation
    INFERENCE = "inference"   # Derived from data
    CORRELATION = "correlation" # Statistical correlation
    CAUSATION = "causation"    # Causal claim (requires caveats)
    PREDICTION = "prediction"  # Forward projection
    RECOMMENDATION = "recommendation"  # Action suggestion


@dataclass
class Claim:
    """A claim made during analysis.

    Claims are the conclusions that the agent makes based on
    the evidence. They must be linked to evidence and may
    have limitations or caveats attached.
    """

    claim_id: str
    task_id: str
    claim_type: ClaimType
    statement: str
    confidence: float = 1.0  # 0-1
    status: ClaimStatus = ClaimStatus.DRAFT
    evidence_ids: list[str] = field(default_factory=list)
    hypothesis_ids: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    supporting_observations: list[str] = field(default_factory=list)
    conflicting_observations: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    verified_at: datetime | None = None
    verified_by: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "claim_id": self.claim_id,
            "task_id": self.task_id,
            "claim_type": self.claim_type.value,
            "statement": self.statement,
            "confidence": self.confidence,
            "status": self.status.value,
            "evidence_ids": self.evidence_ids,
            "hypothesis_ids": self.hypothesis_ids,
            "limitations": self.limitations,
            "caveats": self.caveats,
            "supporting_observations": self.supporting_observations,
            "conflicting_observations": self.conflicting_observations,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verified_by": self.verified_by,
            "metadata": self.metadata,
        }


class ClaimManager:
    """Manages claims throughout the analysis lifecycle.

    The manager handles:
    1. Claim creation
    2. Evidence linking
    3. Verification workflows
    4. Status transitions
    5. Conflict detection
    """

    def __init__(self) -> None:
        """Initialize claim manager."""
        self._claims: dict[str, Claim] = {}

    def create_claim(
        self,
        task_id: str,
        claim_type: ClaimType,
        statement: str,
        confidence: float = 1.0,
        evidence_ids: list[str] | None = None,
        hypothesis_ids: list[str] | None = None,
        limitations: list[str] | None = None,
    ) -> Claim:
        """Create a new claim.

        Args:
            task_id: Task identifier
            claim_type: Type of claim
            statement: The claim statement
            confidence: Confidence level (0-1)
            evidence_ids: Supporting evidence IDs
            hypothesis_ids: Related hypothesis IDs
            limitations: Known limitations

        Returns:
            Created claim
        """
        claim = Claim(
            claim_id=str(uuid.uuid4()),
            task_id=task_id,
            claim_type=claim_type,
            statement=statement,
            confidence=confidence,
            evidence_ids=evidence_ids or [],
            hypothesis_ids=hypothesis_ids or [],
            limitations=limitations or [],
        )

        self._claims[claim.claim_id] = claim
        return claim

    def update_claim(self, claim_id: str, **kwargs: Any) -> Claim | None:
        """Update claim attributes."""
        claim = self._claims.get(claim_id)
        if not claim:
            return None

        for key, value in kwargs.items():
            if hasattr(claim, key):
                setattr(claim, key, value)

        claim.updated_at = datetime.now(UTC)
        return claim

    def add_evidence(self, claim_id: str, evidence_id: str) -> None:
        """Add supporting evidence to a claim."""
        claim = self._claims.get(claim_id)
        if claim and evidence_id not in claim.evidence_ids:
            claim.evidence_ids.append(evidence_id)
            claim.updated_at = datetime.now(UTC)

    def add_conflict(self, claim_id: str, observation_id: str) -> None:
        """Record conflicting observation."""
        claim = self._claims.get(claim_id)
        if claim and observation_id not in claim.conflicting_observations:
            claim.conflicting_observations.append(observation_id)
            claim.updated_at = datetime.now(UTC)

    def verify_claim(
        self,
        claim: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> bool:
        """Verify a claim against evidence.

        Args:
            claim: Claim dictionary
            evidence: List of evidence items

        Returns:
            True if claim is verified
        """
        claim_id = claim.get("claim_id", "")
        c = self._claims.get(claim_id)
        if not c:
            return False

        # Get supporting evidence
        supporting_evidence = [
            e for e in evidence
            if e.get("evidence_id", "") in c.evidence_ids
        ]

        if not supporting_evidence:
            return False

        # Check evidence validity
        valid_evidence = [
            e for e in supporting_evidence
            if e.get("validation_status") == "VALID"
        ]

        # Verify based on claim type
        if c.claim_type == ClaimType.FACT:
            # Facts require direct evidence
            return len(valid_evidence) > 0

        elif c.claim_type == ClaimType.INFERENCE:
            # Inferences require multiple supporting evidence
            return len(valid_evidence) >= 1

        elif c.claim_type == ClaimType.CORRELATION:
            # Correlations need statistical evidence
            return len(valid_evidence) > 0

        elif c.claim_type == ClaimType.CAUSATION:
            # Causation requires significant evidence AND caveats
            has_caveats = len(c.caveats) > 0
            has_evidence = len(valid_evidence) > 0
            if has_evidence and not has_caveats:
                # Auto-add causation caveat
                c.caveats.append("Correlation does not imply causation")
            return has_evidence

        return False

    def transition_status(
        self,
        claim_id: str,
        new_status: ClaimStatus,
        verified_by: str | None = None,
    ) -> Claim | None:
        """Transition claim to new status.

        Args:
            claim_id: Claim identifier
            new_status: New status
            verified_by: Who/what verified the claim

        Returns:
            Updated claim
        """
        claim = self._claims.get(claim_id)
        if not claim:
            return None

        # Validate transition
        valid_transitions: dict[ClaimStatus, list[ClaimStatus]] = {
            ClaimStatus.DRAFT: [ClaimStatus.SUBMITTED, ClaimStatus.REJECTED],
            ClaimStatus.SUBMITTED: [ClaimStatus.VERIFIED, ClaimStatus.QUALIFIED, ClaimStatus.REJECTED],
            ClaimStatus.VERIFIED: [ClaimStatus.SUPERSEDED],
            ClaimStatus.QUALIFIED: [ClaimStatus.SUPERSEDED, ClaimStatus.REJECTED],
            ClaimStatus.REJECTED: [],  # Terminal
            ClaimStatus.SUPERSEDED: [],  # Terminal
        }

        allowed = valid_transitions.get(claim.status, [])
        if new_status not in allowed:
            return None

        claim.status = new_status
        claim.updated_at = datetime.now(UTC)

        if new_status in (ClaimStatus.VERIFIED, ClaimStatus.QUALIFIED):
            claim.verified_at = datetime.now(UTC)
            claim.verified_by = verified_by or "system"

        return claim

    def get_claims_for_task(self, task_id: str) -> list[Claim]:
        """Get all claims for a task."""
        return [
            c for c in self._claims.values()
            if c.task_id == task_id
        ]

    def get_verified_claims(self, task_id: str) -> list[Claim]:
        """Get verified claims for a task."""
        return [
            c for c in self._claims.values()
            if c.task_id == task_id
            and c.status in (ClaimStatus.VERIFIED, ClaimStatus.QUALIFIED)
        ]

    def detect_conflicts(
        self,
        claim_id: str,
    ) -> list[str]:
        """Detect conflicts with other claims.

        Returns:
            List of conflicting claim IDs
        """
        claim = self._claims.get(claim_id)
        if not claim:
            return []

        conflicts: list[str] = []

        for other_id, other in self._claims.items():
            if other_id == claim_id:
                continue

            # Check for contradictory statements
            if claim.statement.lower() in other.statement.lower():
                continue

            # Check for conflicting observations
            shared_obs = set(claim.supporting_observations) & set(other.conflicting_observations)
            if shared_obs:
                conflicts.append(other_id)

        return conflicts

    def generate_claim_summary(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """Generate a summary of claims for a task."""
        claims = self.get_claims_for_task(task_id)

        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        total_evidence = 0

        for claim in claims:
            by_status[claim.status.value] = by_status.get(claim.status.value, 0) + 1
            by_type[claim.claim_type.value] = by_type.get(claim.claim_type.value, 0) + 1
            total_evidence += len(claim.evidence_ids)

        verified = self.get_verified_claims(task_id)

        return {
            "task_id": task_id,
            "total_claims": len(claims),
            "verified_claims": len(verified),
            "by_status": by_status,
            "by_type": by_type,
            "total_evidence_links": total_evidence,
            "verified": [c.to_dict() for c in verified],
        }
