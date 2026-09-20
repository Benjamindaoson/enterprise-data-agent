"""E2E Demos for P0-D Agent Runtime.

This module provides end-to-end demonstration scenarios for:
1. Finance: Budget variance analysis
2. Sales: Multi-dimensional trend analysis
3. Supply Chain: Contribution and anomaly analysis
"""

import asyncio
from datetime import datetime

from eiw.agent.runtime import create_agent_runtime
from eiw.agent.governance import create_demo_personas, create_demo_session


async def demo_finance_budget_analysis():
    """Demo: Finance Budget Variance Analysis.

    Scenario: Finance analyst wants to understand why Q1 budget was missed.
    """
    print("\n" + "=" * 70)
    print("FINANCE DEMO: Budget Variance Analysis")
    print("=" * 70)

    runtime = create_agent_runtime()
    personas = create_demo_personas()
    session = create_demo_session(personas["finance_carol"])

    questions = [
        "What was the variance between actual and budgeted revenue for Q1 2024?",
        "Break down the revenue variance by product category",
        "Which regions contributed most to the unfavorable variance?",
        "What drove the cost increase - price or volume effects?",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n[{i}] Question: {question}")
        print("-" * 60)

        result = await runtime.analyze(question, domain="finance", session=session)

        print(f"Status: {result.status.value}")
        print(f"Duration: {result.duration_ms}ms")
        print(f"Steps executed: {result.steps_executed}")

        if result.observations:
            print("\nObservations:")
            for obs in result.observations[:3]:
                print(f"  - {obs.get('content', '')[:100]}")

        if result.claims:
            print("\nClaims:")
            for claim in result.claims[:2]:
                print(f"  - {claim.get('statement', '')}")

    print("\n" + "=" * 70)
    print("Demo Complete")
    print("=" * 70)


async def demo_sales_trend_analysis():
    """Demo: Sales Multi-Dimensional Trend Analysis.

    Scenario: Sales manager wants to understand sales performance trends.
    """
    print("\n" + "=" * 70)
    print("SALES DEMO: Multi-Dimensional Trend Analysis")
    print("=" * 70)

    runtime = create_agent_runtime()
    personas = create_demo_personas()
    session = create_demo_session(personas["sales_david"])

    questions = [
        "Show me the sales trend for the past 6 months",
        "Compare sales performance between this quarter and last quarter",
        "Which product categories are growing the fastest?",
        "Identify any anomalies in the sales data",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n[{i}] Question: {question}")
        print("-" * 60)

        result = await runtime.analyze(question, domain="sales", session=session)

        print(f"Status: {result.status.value}")
        print(f"Duration: {result.duration_ms}ms")
        print(f"Steps executed: {result.steps_executed}")

        if result.final_answer:
            print(f"\nAnswer:\n{result.final_answer[:300]}")

    print("\n" + "=" * 70)
    print("Demo Complete")
    print("=" * 70)


async def demo_supply_chain_analysis():
    """Demo: Supply Chain Contribution and Anomaly Analysis.

    Scenario: Operations manager wants to understand supply chain performance.
    """
    print("\n" + "=" * 70)
    print("SUPPLY CHAIN DEMO: Contribution and Anomaly Analysis")
    print("=" * 70)

    runtime = create_agent_runtime()
    personas = create_demo_personas()
    session = create_demo_session(personas["ops_eve"])

    questions = [
        "What is the contribution of each supplier to total delivery delays?",
        "Show me the trend in warehouse utilization over the past quarter",
        "Detect any anomalies in delivery times",
        "Drill down into the high-delay region to understand root causes",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n[{i}] Question: {question}")
        print("-" * 60)

        result = await runtime.analyze(question, domain="operations", session=session)

        print(f"Status: {result.status.value}")
        print(f"Duration: {result.duration_ms}ms")
        print(f"Steps executed: {result.steps_executed}")

        if result.final_answer:
            print(f"\nAnswer:\n{result.final_answer[:300]}")

    print("\n" + "=" * 70)
    print("Demo Complete")
    print("=" * 70)


async def demo_multi_step_investigation():
    """Demo: Multi-Step Investigation with Hypothesis Testing.

    This demonstrates the full agent loop with:
    - Intent resolution
    - Plan creation
    - Tool execution
    - Observation recording
    - Hypothesis updates
    - Synthesis
    """
    print("\n" + "=" * 70)
    print("MULTI-STEP INVESTIGATION DEMO")
    print("=" * 70)

    runtime = create_agent_runtime()

    # Complex investigation question
    question = """
    Investigate why customer satisfaction dropped in March.
    We need to understand:
    1. Which product categories had the most complaints
    2. Whether this is a regional issue or company-wide
    3. If there are any correlations with delivery times
    """

    print(f"\nInvestigation Question:\n{question}")
    print("-" * 60)

    result = await runtime.analyze(question, domain="operations")

    print(f"\nStatus: {result.status.value}")
    print(f"Duration: {result.duration_ms}ms")
    print(f"Steps executed: {result.steps_executed}")
    print(f"Steps failed: {result.steps_failed}")

    if result.intent:
        print(f"\nResolved Intent:")
        print(f"  - Objective: {result.intent.get('objective', 'N/A')}")
        print(f"  - Analysis type: {result.intent.get('analysis_type', 'N/A')}")
        print(f"  - Metrics: {result.intent.get('selected_metrics', [])}")

    if result.plan_steps:
        print(f"\nExecution Plan ({len(result.plan_steps)} steps):")
        for i, step in enumerate(result.plan_steps[:5], 1):
            print(f"  {i}. {step.get('purpose', 'N/A')} [{step.get('tool', 'N/A')}]")

    if result.observations:
        print(f"\nObservations ({len(result.observations)}):")
        for obs in result.observations[:3]:
            print(f"  - {obs.get('content', '')[:100]}")

    if result.claims:
        print(f"\nDerived Claims ({len(result.claims)}):")
        for claim in result.claims:
            print(f"  - {claim.get('statement', '')}")

    if result.final_answer:
        print(f"\nFinal Answer:\n{result.final_answer}")

    print("\n" + "=" * 70)
    print("Demo Complete")
    print("=" * 70)


async def run_all_demos():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("ENTERPRISE DATA AGENT v2.0 - E2E DEMOS")
    print("=" * 70)

    try:
        await demo_finance_budget_analysis()
    except Exception as e:
        print(f"Finance demo error: {e}")

    try:
        await demo_sales_trend_analysis()
    except Exception as e:
        print(f"Sales demo error: {e}")

    try:
        await demo_supply_chain_analysis()
    except Exception as e:
        print(f"Supply chain demo error: {e}")

    try:
        await demo_multi_step_investigation()
    except Exception as e:
        print(f"Multi-step demo error: {e}")

    print("\n" + "=" * 70)
    print("ALL DEMOS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_demos())
