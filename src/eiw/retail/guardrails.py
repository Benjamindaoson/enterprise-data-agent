"""Preflight behavioral guardrails for the Retail BA domain.

These checks do not replace model safety policy. They define deterministic
product boundaries that are independently testable: scope, available data,
causal language, destructive instructions, ambiguity, and prompt injection.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field

from eiw.retail.models import RetailAnalysisRequest


class GuardrailAction(StrEnum):
    ANALYZE = "ANALYZE"
    QUALIFY = "QUALIFY"
    CLARIFY = "CLARIFY"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    REFUSE = "REFUSE"


class RetailGuardrailDecision(BaseModel):
    action: GuardrailAction
    reason: str
    matched_rules: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RetailRequestGuard:
    """Fail closed on unsupported or adversarial requests before tool execution."""

    _PROMPT_INJECTION = (
        "ignore previous instructions",
        "ignore all previous",
        "system prompt",
        "developer message",
        "reveal your prompt",
        "hidden instructions",
        "bypass guardrail",
        "jailbreak",
        "act as unrestricted",
    )
    _DESTRUCTIVE = (
        r"\bdrop\s+table\b",
        r"\btruncate\s+table\b",
        r"\bdelete\s+from\b",
        r"\binsert\s+into\b",
        r"\bupdate\s+\w+\s+set\b",
        r"\bunion\s+select\b",
        r"\bpg_sleep\s*\(",
        r"\bxp_cmdshell\b",
        r"\brm\s+-rf\b",
    )
    _IRRELEVANT = (
        "write me a poem",
        "write a poem",
        "recipe for",
        "medical diagnosis",
        "legal advice",
        "plan my vacation",
        "translate this sentence",
        "tell me a joke",
        "who won the election",
    )
    _UNAVAILABLE_DATA = (
        "gross margin",
        "profit margin",
        "net profit",
        "inventory",
        "stock on hand",
        "supplier cost",
        "cost of goods",
        "competitor",
        "web traffic",
        "website traffic",
        "employee",
        "headcount",
        "country",
        "city",
        "device",
        "weather",
    )
    _AMBIGUOUS_EXACT = {
        "analyze this",
        "analyse this",
        "what's wrong",
        "what is wrong",
        "what happened",
        "tell me more",
        "look into this",
        "investigate",
        "分析一下",
        "看看这个",
        "怎么回事",
    }
    _CAUSAL = (
        "did promotion cause",
        "did the promotion cause",
        "did coupon cause",
        "did the coupon cause",
        "did display",
        "did the display",
        "causal effect",
        "caused the sales",
        "prove that",
        "incremental lift",
        "because of the coupon",
        "because of promotion",
        "因果",
        "导致销售",
        "证明促销",
    )
    _IMPOSSIBLE = (
        "predict exactly",
        "guarantee next",
        "guarantee future",
        "100% certainty",
        "with certainty",
        "perfectly predict",
        "必然预测",
        "百分之百预测",
    )

    def evaluate(
        self,
        request: RetailAnalysisRequest,
        *,
        available_weeks: set[int] | None = None,
    ) -> RetailGuardrailDecision:
        question = " ".join(request.question.lower().split())

        if any(token in question for token in self._PROMPT_INJECTION):
            return RetailGuardrailDecision(
                action=GuardrailAction.REFUSE,
                reason="Prompt-injection instructions are outside the business-analysis contract.",
                matched_rules=["prompt_injection"],
            )

        if any(re.search(pattern, question) for pattern in self._DESTRUCTIVE):
            return RetailGuardrailDecision(
                action=GuardrailAction.REFUSE,
                reason="Destructive SQL or shell instructions are not executable by the BA Agent.",
                matched_rules=["destructive_instruction"],
            )

        if any(token in question for token in self._IRRELEVANT):
            return RetailGuardrailDecision(
                action=GuardrailAction.REFUSE,
                reason="The request is outside the Retail Business Analysis domain.",
                matched_rules=["out_of_scope"],
            )

        if any(token in question for token in self._IMPOSSIBLE):
            return RetailGuardrailDecision(
                action=GuardrailAction.REFUSE,
                reason="The available observational history cannot support guaranteed future predictions.",
                matched_rules=["impossible_prediction"],
                limitations=["Use scenario analysis or a separately validated forecasting workflow instead."],
            )

        if available_weeks and (request.current_weeks or request.previous_weeks):
            requested = set(request.current_weeks) | set(request.previous_weeks)
            unavailable = sorted(requested - available_weeks)
            if unavailable:
                return RetailGuardrailDecision(
                    action=GuardrailAction.DATA_UNAVAILABLE,
                    reason=f"Requested weeks are not present in the connected dataset: {unavailable}.",
                    matched_rules=["time_out_of_range"],
                    limitations=["Choose periods from the dataset's available week range."],
                )

        unavailable_terms = [
            token for token in self._UNAVAILABLE_DATA if token in question
        ]
        if unavailable_terms:
            return RetailGuardrailDecision(
                action=GuardrailAction.DATA_UNAVAILABLE,
                reason=(
                    "The connected retail semantic package does not contain the requested "
                    f"data: {', '.join(unavailable_terms[:3])}."
                ),
                matched_rules=["missing_data"],
                limitations=[
                    "Connect an approved source and extend the semantic package before analysis."
                ],
            )

        normalized = question.strip(" ?.!。！？")
        vague_phrase = any(
            phrase in normalized
            for phrase in (
                "analyze this",
                "analyse this",
                "what's wrong",
                "what is wrong",
                "what happened",
                "tell me more",
                "look into this",
                "investigate",
                "check this",
                "analyze it",
                "any issues",
                "thoughts",
                "look at this",
                "分析一下",
                "看看这个",
                "怎么回事",
            )
        )
        business_anchor = any(
            token in normalized
            for token in (
                "sales",
                "revenue",
                "store",
                "category",
                "commodity",
                "product",
                "promotion",
                "customer",
                "basket",
                "销售",
                "门店",
                "品类",
                "促销",
                "客户",
            )
        )
        if normalized in self._AMBIGUOUS_EXACT or len(normalized.split()) <= 2 or (
            vague_phrase and not business_anchor
        ):
            return RetailGuardrailDecision(
                action=GuardrailAction.CLARIFY,
                reason="The business question is too underspecified to choose a defensible analysis.",
                matched_rules=["ambiguous_request"],
                limitations=[
                    "Specify the KPI, business slice, or decision you want to investigate."
                ],
            )

        if any(token in question for token in self._CAUSAL):
            return RetailGuardrailDecision(
                action=GuardrailAction.QUALIFY,
                reason=(
                    "The request asks for causal interpretation, but the connected retail "
                    "dataset is observational."
                ),
                matched_rules=["unsupported_causality"],
                limitations=[
                    "Promotion, display, campaign, and coupon results are reported as observed "
                    "associations unless a valid experimental or matched design is supplied."
                ],
            )

        return RetailGuardrailDecision(
            action=GuardrailAction.ANALYZE,
            reason="Request is within the governed retail-analysis contract.",
        )
