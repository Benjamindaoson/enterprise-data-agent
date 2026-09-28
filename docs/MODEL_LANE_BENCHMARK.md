# Retail Model-Lane Benchmark

This benchmark is designed to answer one system question: **when does
model-driven Agent orchestration improve the BA Agent enough to justify its
latency, cost, and extra failure surface?**

## Comparable lanes

Every lane uses the same retail data, analytical workers, benchmark cases and
scoring functions.

| Lane | Model decisions |
| --- | --- |
| deterministic | none |
| single-agent | one global model plan selects workstreams and bounded specialist skills |
| supervisor | model chooses initial/replanned workstreams; specialist skills remain deterministic |
| supervisor+specialists | model chooses workstreams and each specialist's bounded skills |

The runner records task success, end-to-end latency, re-plan rate, model calls,
prompt/completion tokens, configured estimated provider cost, invalid
response/choice rate, and deterministic fallback count.

## Live providers

The manual workflow `.github/workflows/retail-model-lane.yml` expects three
OpenAI-compatible endpoints labeled Qwen, GPT and Claude. A provider with a
native non-OpenAI protocol must be placed behind a compatible gateway; the
benchmark does not pretend protocol compatibility that has not been configured.

Required GitHub secrets:

- `EIW_BENCH_QWEN_BASE_URL`, `EIW_BENCH_QWEN_MODEL`, `EIW_BENCH_QWEN_API_KEY`
- `EIW_BENCH_GPT_BASE_URL`, `EIW_BENCH_GPT_MODEL`, `EIW_BENCH_GPT_API_KEY`
- `EIW_BENCH_CLAUDE_BASE_URL`, `EIW_BENCH_CLAUDE_MODEL`, `EIW_BENCH_CLAUDE_API_KEY`

Optional repository variables provide input/output USD cost per million tokens.

The live workflow uses `--require-live`; it fails rather than silently
dropping a missing provider. Therefore a three-provider artifact is evidence
that all three endpoints were actually configured.

## Claim discipline

Normal CI executes the deterministic reference and unit-level model policy
contracts. Live Qwen/GPT/Claude results are reportable only after the manual
workflow executes against real endpoints. Missing credentials are never
replaced with mocks or synthetic scores.
