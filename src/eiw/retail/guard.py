"""Deterministic request guard for adversarial retail BA workloads."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from eiw.retail.data import RetailDataEngine
from eiw.retail.models import RetailAnalysisRequest


class RequestDisposition(StrEnum):
    ALLOW = "allow"
    CLARIFY = "clarify"
    REJECT = "reject"
    QUALIFY = "qualify"


class GuardDecision(BaseModel):
    disposition: RequestDisposition
    code: str
    reason: str


class RetailRequestGuard:
    """Fail closed on unsafe/unsupported requests without inventing evidence."""

    _PROMPT_INJECTION = (
        "ignore all previous",
        "ignore previous instructions",
        "override developer",
        "system prompt",
        "developer prompt",
        "developer message",
        "jailbreak",
        "higher-priority instructions",
        "new system message",
        "private chain-of-thought",
        "hidden chain-of-thought",
        "reveal every hidden instruction",
        "override the agent runtime",
    )
    _UNSAFE = (
        "execute shell",
        "shell command",
        "rm -rf",
        "drop every database",
        "drop table",
        "delete from",
        "read environment variables",
        "api keys",
        "credentials",
        "/etc/passwd",
        "arbitrary files",
        "unrestricted sql",
        "bypass the sandbox",
        "outbound network",
        "delete the evidence",
        "write to the source database",
        "update the source rows",
        "escalate privileges",
        "disable the read-only",
        "turn off read-only",
        "hidden schemas",
        "external url",
    )
    _IRRELEVANT = (
        "haiku",
        "football game",
        "sourdough",
        "love poem",
        "todo app",
        "vacation",
        "quantum entanglement",
        "bedtime story",
        "gaming laptop",
        "wedding invitation",
        "today's weather",
        "weather today",
        "joke about",
        "sonnet",
        "tune a guitar",
        "dinner menu",
    )
    _AMBIGUOUS = (
        "analyze this",
        "what happened",
        "show me performance",
        "anything interesting",
        "look into it",
        "give me the numbers",
        "how are things going",
        "do an analysis",
        "what should i know",
        "check the business",
        "tell me what's important",
        "give me an update",
        "take a look at the latest",
        "analyze what matters",
        "give me an insight",
    )
    _UNSUPPORTED = (
        "exact sales to the cent",
        "exact sales number",
        "private reasoning",
        "recover deleted",
        "customer passwords",
        "real names",
        "anonymous household",
        "inventory",
        "out of stock",
        "stockout",
        "gross profit",
        "profit after tax",
        "gross margin",
        "margin by store",
        "cost-of-goods",
        "labor cost",
        "employee productivity",
        "staffing",
        "competitor prices",
        "customer support",
        "support tickets",
        "warehouse",
        "delivery lateness",
        "web traffic",
        "return rates",
        "supplier lead",
        "payroll",
        "session duration",
        "counterfactual world",
        "exact future coupon",
    )
    _CAUSAL = (
        "caused",
        "causal",
        "incremental lift",
        "incremental revenue",
        "treatment effect",
        "would disappear if",
        "would have been",
        "prove that promotions",
        "prove coupon",
        "causal roi",
    )
    _CONFLICTS = (
        ("by store", "do not use the store"),
        ("rank stores", "do not use any store"),
        ("category", "excluding all category"),
        ("categories", "forbidding product"),
        ("group by store", "no store identifiers"),
        ("customer income", "do not use demographics"),
        ("promotion performance", "exclude every promotion"),
        ("display location", "excluding display"),
        ("display location", "without using promotion"),
        ("compare weeks", "ignoring the time"),
        ("store and not-store", "store and not-store"),
        ("commodity", "do not access product"),
        ("household drivers", "without using household"),
        ("coupon behavior", "without using coupon"),
        ("basket-level", "do not access basket"),
    )
    _SCHEMA_DISTRACTOR = (
        "distractor",
        "fake_sales",
        "imaginary_table",
        "nonexistent schema",
        "fabricated column",
        "invented field",
        "made-up dimension",
        "fake schema",
        "pasted note",
        "disregard select",
        "orders_v99",
        "lunar_sales",
        "secret_margin",
    )

    def assess(
        self,
        request: RetailAnalysisRequest,
        data: RetailDataEngine,
    ) -> GuardDecision:
        text = " ".join(request.question.lower().split())

        if any(token in text for token in self._PROMPT_INJECTION):
            return GuardDecision(
                disposition=RequestDisposition.REJECT,
                code="PROMPT_INJECTION",
                reason="Prompt-injection instructions are outside the BA Agent contract.",
            )
        if any(token in text for token in self._UNSAFE):
            return GuardDecision(
                disposition=RequestDisposition.REJECT,
                code="UNSAFE_INSTRUCTION",
                reason="The request asks for unsafe or non-read-only execution.",
            )

        range_decision = self._validate_weeks(request, data)
        if range_decision is not None:
            return range_decision

        for left, right in self._CONFLICTS:
            if left in text and right in text:
                return GuardDecision(
                    disposition=RequestDisposition.CLARIFY,
                    code="CONFLICTING_CONSTRAINTS",
                    reason="The requested dimension conflicts with an explicit exclusion.",
                )

        if any(token in text for token in self._IRRELEVANT):
            return GuardDecision(
                disposition=RequestDisposition.REJECT,
                code="IRRELEVANT_REQUEST",
                reason="The request is unrelated to governed business analysis.",
            )

        if any(token in text for token in self._AMBIGUOUS):
            return GuardDecision(
                disposition=RequestDisposition.CLARIFY,
                code="CLARIFICATION_REQUIRED",
                reason="The business question does not identify a supported analytical goal.",
            )

        # Schema distractors must not override the governed semantic package.
        schema_distractor = any(token in text for token in self._SCHEMA_DISTRACTOR)
        if not schema_distractor and any(token in text for token in self._UNSUPPORTED):
            return GuardDecision(
                disposition=RequestDisposition.REJECT,
                code="UNSUPPORTED_DATA",
                reason="The requested evidence is not available in the connected retail data.",
            )

        if any(token in text for token in self._CAUSAL):
            return GuardDecision(
                disposition=RequestDisposition.QUALIFY,
                code="OBSERVATIONAL_ONLY",
                reason=(
                    "The retail dataset is observational; the analysis can report "
                    "associations but cannot establish causal treatment effects."
                ),
            )

        return GuardDecision(
            disposition=RequestDisposition.ALLOW,
            code="ALLOW",
            reason="Request is within the governed retail analytical contract.",
        )

    @staticmethod
    def _validate_weeks(
        request: RetailAnalysisRequest,
        data: RetailDataEngine,
    ) -> GuardDecision | None:
        requested = [*request.current_weeks, *request.previous_weeks]
        if not requested:
            return None
        rows = data.query_readonly(
            "SELECT MIN(week_no) AS min_week, MAX(week_no) AS max_week "
            "FROM retail_transactions"
        )
        if not rows:
            return None
        minimum = int(rows[0]["min_week"])
        maximum = int(rows[0]["max_week"])
        if any(week < minimum or week > maximum for week in requested):
            return GuardDecision(
                disposition=RequestDisposition.REJECT,
                code="OUT_OF_RANGE",
                reason=f"Requested weeks must be within [{minimum}, {maximum}].",
            )
        return None
