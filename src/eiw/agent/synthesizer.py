"""Report Synthesizer for Enterprise Data Agent.

Synthesizes analysis results into structured reports with:
- Executive summary
- Key findings
- Supporting evidence
- Recommendations
- Limitations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ReportSection:
    """A section of a report."""

    title: str
    content: str
    order: int
    section_type: str  # summary, finding, evidence, recommendation, limitation


@dataclass
class AnalysisReport:
    """A complete analysis report."""

    report_id: str
    task_id: str
    question: str
    sections: list[ReportSection] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    format: str = "markdown"

    def to_markdown(self) -> str:
        """Convert report to Markdown format."""
        lines = [
            f"# {self.question}",
            "",
            f"**Generated:** {self.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
        ]

        for section in sorted(self.sections, key=lambda s: s.order):
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")

        # Add metadata if present
        if self.metadata:
            lines.append("## Report Metadata")
            lines.append("")
            for key, value in self.metadata.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "task_id": self.task_id,
            "question": self.question,
            "sections": [
                {"title": s.title, "content": s.content, "order": s.order, "type": s.section_type}
                for s in self.sections
            ],
            "claims": self.claims,
            "evidence_summary": self.evidence_summary,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "format": self.format,
        }


class ReportSynthesizer:
    """Synthesizes analysis results into structured reports.

    The synthesizer:
    1. Collects all findings from the analysis
    2. Organizes claims and evidence
    3. Generates executive summary
    4. Adds recommendations
    5. Documents limitations
    6. Formats the final report
    """

    def synthesize(
        self,
        task_id: str,
        question: str,
        observations: list[dict[str, Any]],
        claims: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        hypotheses: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> AnalysisReport:
        """Synthesize analysis results into a complete report.

        Args:
            task_id: Task identifier
            question: Original business question
            observations: List of observations from analysis
            claims: List of claims made during analysis
            evidence: List of evidence items
            hypotheses: List of hypotheses and their states
            context: Optional additional context

        Returns:
            Complete analysis report
        """
        import uuid

        report_id = str(uuid.uuid4())
        sections: list[ReportSection] = []
        order = 0

        # 1. Executive Summary
        order += 1
        summary_content = self._generate_summary(claims, hypotheses, observations)
        sections.append(
            ReportSection(
                title="Executive Summary",
                content=summary_content,
                order=order,
                section_type="summary",
            )
        )

        # 2. Key Findings
        order += 1
        findings_content = self._generate_findings(claims, observations)
        sections.append(
            ReportSection(
                title="Key Findings",
                content=findings_content,
                order=order,
                section_type="finding",
            )
        )

        # 3. Detailed Analysis
        if observations:
            order += 1
            analysis_content = self._generate_detailed_analysis(observations, hypotheses)
            sections.append(
                ReportSection(
                    title="Detailed Analysis",
                    content=analysis_content,
                    order=order,
                    section_type="analysis",
                )
            )

        # 4. Supporting Evidence
        order += 1
        evidence_content = self._generate_evidence_section(evidence)
        sections.append(
            ReportSection(
                title="Supporting Evidence",
                content=evidence_content,
                order=order,
                section_type="evidence",
            )
        )

        # 5. Recommendations
        order += 1
        recommendations_content = self._generate_recommendations(claims, hypotheses)
        sections.append(
            ReportSection(
                title="Recommendations",
                content=recommendations_content,
                order=order,
                section_type="recommendation",
            )
        )

        # 6. Limitations
        order += 1
        limitations_content = self._generate_limitations(observations, hypotheses, context)
        sections.append(
            ReportSection(
                title="Limitations",
                content=limitations_content,
                order=order,
                section_type="limitation",
            )
        )

        # Create report
        report = AnalysisReport(
            report_id=report_id,
            task_id=task_id,
            question=question,
            sections=sections,
            claims=claims,
            evidence_summary=self._summarize_evidence(evidence),
            metadata={
                "total_observations": len(observations),
                "total_claims": len(claims),
                "total_evidence": len(evidence),
                "hypotheses_tested": len(hypotheses),
                "hypotheses_resolved": len([h for h in hypotheses if h.get("is_resolved", False)]),
            },
        )

        return report

    def _generate_summary(
        self,
        claims: list[dict[str, Any]],
        hypotheses: list[dict[str, Any]],
        observations: list[dict[str, Any]],
    ) -> str:
        """Generate executive summary."""
        lines = []

        if not claims:
            lines.append("No conclusive findings were generated from this analysis.")
            return "\n".join(lines)

        # Main conclusion
        primary_claims = [c for c in claims if c.get("status") == "VERIFIED"]
        if primary_claims:
            lines.append(f"**Primary Finding:** {primary_claims[0].get('statement', 'N/A')}")
            lines.append("")

        # Summary statistics
        lines.append("**Analysis Summary:**")
        lines.append(f"- {len(observations)} data observations analyzed")
        lines.append(f"- {len(claims)} claims made, {len([c for c in claims if c.get('status') == 'VERIFIED'])} verified")
        lines.append(f"- {len(hypotheses)} hypotheses investigated")

        return "\n".join(lines)

    def _generate_findings(
        self,
        claims: list[dict[str, Any]],
        observations: list[dict[str, Any]],
    ) -> str:
        """Generate key findings section."""
        lines = []

        if not claims:
            lines.append("No verified claims were generated from this analysis.")
            return "\n".join(lines)

        # Verified claims
        verified = [c for c in claims if c.get("status") == "VERIFIED"]
        if verified:
            lines.append("### Verified Findings")
            lines.append("")
            for i, claim in enumerate(verified, 1):
                lines.append(f"{i}. {claim.get('statement', 'N/A')}")
            lines.append("")

        # Qualified claims
        qualified = [c for c in claims if c.get("status") == "QUALIFIED"]
        if qualified:
            lines.append("### Qualified Findings (with caveats)")
            lines.append("")
            for i, claim in enumerate(qualified, 1):
                lines.append(f"{i}. {claim.get('statement', 'N/A')}")
                if claim.get("limitations"):
                    lines.append(f"   - *Note:* {', '.join(claim['limitations'])}")
            lines.append("")

        return "\n".join(lines)

    def _generate_detailed_analysis(
        self,
        observations: list[dict[str, Any]],
        hypotheses: list[dict[str, Any]],
    ) -> str:
        """Generate detailed analysis section."""
        lines = []

        # Observation summary
        lines.append("### Observation Summary")
        lines.append("")
        lines.append(f"Total observations: {len(observations)}")
        lines.append("")

        # Key metrics from observations
        metric_obs = [o for o in observations if o.get("observation_type") == "metric_value"]
        if metric_obs:
            lines.append("#### Key Metrics")
            lines.append("")
            for obs in metric_obs[:5]:  # Limit to 5
                values = obs.get("numeric_values", {})
                for key, value in values.items():
                    lines.append(f"- **{key}:** {value}")
            lines.append("")

        # Hypothesis outcomes
        if hypotheses:
            lines.append("### Hypothesis Outcomes")
            lines.append("")
            for h in hypotheses:
                state = h.get("state", "unknown")
                statement = h.get("statement", "N/A")
                lines.append(f"- **{statement}** — {state.upper()}")
            lines.append("")

        return "\n".join(lines)

    def _generate_evidence_section(self, evidence: list[dict[str, Any]]) -> str:
        """Generate supporting evidence section."""
        lines = []

        if not evidence:
            lines.append("No explicit evidence records were generated.")
            return "\n".join(lines)

        lines.append(f"Total evidence items: {len(evidence)}")
        lines.append("")

        for i, e in enumerate(evidence[:10], 1):  # Limit to 10
            lines.append(f"### Evidence {i}")
            lines.append("")
            lines.append(f"- **Type:** {e.get('computation_identifier', 'N/A')}")
            lines.append(f"- **Metric Version:** {e.get('metric_version', 'N/A')}")
            lines.append(f"- **Dataset:** {e.get('dataset_snapshot', {}).get('identifier', 'N/A')}")
            lines.append(f"- **Validations:** {', '.join(e.get('validation', ['none']))}")
            lines.append("")

        return "\n".join(lines)

    def _generate_recommendations(
        self,
        claims: list[dict[str, Any]],
        hypotheses: list[dict[str, Any]],
    ) -> str:
        """Generate recommendations section."""
        lines = []

        if not claims:
            lines.append("No recommendations can be made without verified findings.")
            return "\n".join(lines)

        lines.append("Based on the analysis, the following actions are recommended:")

        # Recommendations based on claims
        verified_claims = [c for c in claims if c.get("status") == "VERIFIED"]
        if verified_claims:
            for claim in verified_claims[:3]:
                lines.append("")
                lines.append(f"1. **{claim.get('statement', 'N/A')}**")
                # Generic recommendation based on claim type
                claim_type = claim.get("type", "")
                if claim_type == "FACT":
                    lines.append("   - This finding should be incorporated into regular reporting.")

        # Recommendations based on unresolved hypotheses
        unresolved = [h for h in hypotheses if not h.get("is_resolved", False)]
        if unresolved:
            lines.append("")
            lines.append("### Further Investigation Needed")
            for h in unresolved[:3]:
                lines.append(f"- {h.get('statement', 'N/A')}")

        return "\n".join(lines)

    def _generate_limitations(
        self,
        observations: list[dict[str, Any]],
        hypotheses: list[dict[str, Any]],
        context: dict[str, Any] | None,
    ) -> str:
        """Generate limitations section."""
        lines = []

        limitations_found: set[str] = set()

        # Check for limitations in claims
        for claim in context.get("claims", []) if context else []:
            for limit in claim.get("limitations", []):
                limitations_found.add(limit)

        # Check for unresolved hypotheses
        unresolved = [h for h in hypotheses if not h.get("is_resolved", False)]
        if unresolved:
            limitations_found.add(
                "Some hypotheses could not be fully resolved with available data."
            )

        # Add generic limitations
        limitations_found.add(
            "Analysis is based on historical data and may not predict future trends."
        )
        limitations_found.add(
            "Correlation does not imply causation in attribution analysis."
        )

        if limitations_found:
            lines.append("This analysis has the following limitations:")
            for limit in sorted(limitations_found):
                lines.append(f"- {limit}")
        else:
            lines.append("No significant limitations were identified in this analysis.")

        return "\n".join(lines)

    def _summarize_evidence(self, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        """Create evidence summary."""
        return {
            "total_count": len(evidence),
            "by_type": {},
            "validation_summary": {},
        }
