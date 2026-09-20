# P9–P12 Execution Report

This document records what is implemented, what is automatically verified, and
what still requires an external GPU or real proprietary business integration.

## P9 — BusinessAgentBench-Hard-v1

Implemented in `src/eiw/benchmark/`.

The hard environment tests:

- partial observability;
- noisy and conflicting evidence;
- deterministic tool failure / timeout;
- delayed reward;
- tool and token budget trade-offs;
- memory-dependent decisions;
- context drift;
- unsafe writes and approval boundaries;
- multiple valid evidence paths;
- retry and replanning.

Reference policies:

- Direct;
- Random;
- PromptHeuristic;
- Expert.

A dedicated Tiny Transformer policy is trained with SFT and then GRPO-style
group-relative policy optimization on the hard environment. Held-out results are
written to `artifacts/hard-benchmark/results.json`.

Run:

```bash
make setup-training
make benchmark-hard
make train-hard
```

## P10 — BusinessAgentBench-RealData-v1

Official public sources:

- UCI Bank Marketing — DOI `10.24432/C5K306`, CC BY 4.0.
- UCI Online Retail — DOI `10.24432/C5BW33`, CC BY 4.0.
- Existing pinned Iowa wholesale snapshot for governed analytics.

The benchmark explicitly includes:

1. Analytics
2. Attribution
3. Marketing Budget
4. Sales Expansion
5. Monetization
6. Tool Use
7. Recovery
8. Safety

Raw public records are downloaded into the artifact directory and are not
committed to the repository. The benchmark stores source metadata, derived
profiles and task definitions.

Run the lightweight campaign/conversion build:

```bash
python scripts/build_real_business_benchmark.py --bank-only
```

Run the full Bank Marketing + Online Retail build:

```bash
pip install -e '.[benchmark]'
python scripts/build_real_business_benchmark.py
```

## P11 — Real open-weight LLM Agent

Implemented in `src/eiw/llm_agent/`.

The default smoke model is `Qwen/Qwen3-0.6B`; the same action-policy interface
supports larger Qwen3 models such as `Qwen/Qwen3-4B-Instruct-2507`.

The LLM is evaluated as an actual causal-language-model policy:

```text
BusinessAgentBench state
        ↓
governed action prompt
        ↓
causal-LM log probability for each allowed action
        ↓
next tool / skill action
        ↓
environment transition
```

Implemented stages:

- base-model evaluation;
- governed prompt evaluation;
- expert trajectory export;
- LoRA SFT;
- held-out benchmark evaluation;
- action-level grouped relative policy optimization over environment rewards;
- SFT + GRPO held-out evaluation.

Commands:

```bash
make setup-llm
make llm-dataset
python scripts/evaluate_llm_agent.py --model Qwen/Qwen3-0.6B
make llm-sft
python scripts/evaluate_llm_agent.py \
  --model Qwen/Qwen3-0.6B \
  --adapter artifacts/models/qwen3-agent-sft
make llm-grpo
```

A separate `.github/workflows/llm-agent.yml` workflow is intentionally manual
and self-hosted because downloading and training open-weight LLMs on every pull
request would make normal CI slow and expensive.

No real-LLM improvement claim should be made until that workflow has produced
and retained measured Base / Prompt / SFT / SFT+GRPO results.

## P12 — Production Hardening

Implemented production adapters include:

### Durable state

PostgreSQL-compatible persistence for:

- trajectory events;
- checkpoints;
- approval state.

Runtime APIs expose durable checkpoint save/load and HITL approval
request/decision/read endpoints when `EIW_DATABASE_URL` is configured.

### Queue and worker

- in-process `asyncio.Queue`;
- Redis-backed queue;
- async worker;
- retry scheduling.

### Model routing and cost

- Fast / Standard / Reasoning routing;
- complexity and risk routing;
- token-budget-aware route selection;
- provider-neutral explicit price table;
- input/output token and dollar-cost ledger.

### Observability

- OpenTelemetry runtime metrics;
- task success;
- tool calls;
- policy violations;
- token consumption;
- cost;
- latency;
- OTel Collector;
- Prometheus;
- provisioned Grafana dashboard.

### Release safety

A regression/canary gate checks:

- success-rate regression;
- policy-violation regression;
- invalid-action regression;
- cost regression.

Candidate policies that violate configured thresholds exit CI with a non-zero
status.

## CI

The main CI contains four independent verification jobs:

1. `core` — lint, unit/contract tests, hard reference benchmark;
2. `post-training-smoke` — original flywheel plus Hard-v1 SFT/GRPO;
3. `real-data-benchmark` — downloads official Bank Marketing data and builds
   the real-data benchmark;
4. `production-integration` — starts PostgreSQL and Redis services and verifies
   trajectory/checkpoint/approval/queue round trips.

The real open-weight LLM workflow remains separate and manual because it needs
substantially more compute.

## Measured verification snapshot

The current automated verification records:

- Core CI: **535 passed / 2 skipped**.
- Training CI: **7 passed**.
- Production PostgreSQL/Redis integration: **6 passed**.
- RealData-v1: **45,211 Bank Marketing rows** and **541,909 Online Retail rows**,
  producing **9 grounded benchmark tasks**.
- Hard-v1 held-out (12 cases):
  - Direct: 0.0% success, -3.7627 average reward.
  - Random: 0.0% success, -3.8506 average reward.
  - Prompt heuristic: 58.33% success, 0.0115 average reward.
  - SFT: 66.67% success, 0.5926 average reward, 11.63% invalid actions.
  - SFT + GRPO: 66.67% success, 0.6395 average reward, 10.59% invalid actions.

The GRPO result is deliberately described as a reward/action-validity
improvement, **not** a task-success improvement. A CI acceptance gate enforces
that SFT beats the prompt baseline and that GRPO does not regress success while
improving reward and invalid-action rate.

## Truthful boundary

The repository can claim implementation and automated verification only when CI
has run the relevant path.

It must not claim:

- proprietary CRM/campaign production access;
- a real-LLM SFT/GRPO improvement before the manual LLM run exists;
- causal marketing lift from observational public datasets;
- production-scale throughput from CI smoke tests.

Those boundaries are deliberate parts of the system design.
