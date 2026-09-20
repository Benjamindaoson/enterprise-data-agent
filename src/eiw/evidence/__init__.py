"""Evidence and Claims modules for Enterprise Data Agent.

Implements evidence-native analysis with:
- Claim management
- Evidence tracking
- Verification workflows
- Provenance chains
"""

from eiw.evidence.claim import ClaimManager, Claim, ClaimStatus
from eiw.evidence.verifier import EvidenceVerifier, VerificationResult

__all__ = [
    "ClaimManager",
    "Claim",
    "ClaimStatus",
    "EvidenceVerifier",
    "VerificationResult",
]
