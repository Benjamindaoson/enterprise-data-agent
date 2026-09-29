# Hindsight + Agent Lightning integration

The two integrations intentionally sit on different architectural boundaries.

## Hindsight: cross-task long-term memory

`BusinessAgentRuntime` keeps local task/checkpoint memory as the durable runtime
contract and optionally adds Hindsight for cross-task experience.

```text
question
  -> Hindsight recall
  -> non-authoritative memory context
  -> normal Agent Harness
  -> verified result
  -> Hindsight retain
```

Hindsight outage is fail-open for analysis: the core runtime continues without
long-term memory and emits an observable runtime event.

Install and configure:

```bash
pip install -e '.[hindsight]'
export EIW_LONG_TERM_MEMORY_BACKEND=hindsight
export EIW_HINDSIGHT_BASE_URL=http://127.0.0.1:8888
export EIW_HINDSIGHT_API_KEY=
```

The `/api/v1/memory/reflect` endpoint exposes explicit Hindsight reflection.
Reflection is not run automatically on every task because it adds model cost and
latency.

## Agent Lightning: real-Harness rollout and RL bridge

Agent Lightning is a training-plane integration. It never replaces LangGraph,
the Skill registry, ontology, governed tools or evaluation.

When an Agent Lightning controller launches a rollout it injects:

- `AGL_OPENAI_BASE_URL`
- `AGL_EVENT_URL`
- `AGL_KEY`

The Retail Supervisor, specialist policies and AI Coding model automatically use
the Agent Lightning OpenAI-compatible proxy while the rest of the real Harness
stays unchanged. Model requests are therefore collected by Agent Lightning.

One rollout:

```bash
export AGL_OPENAI_BASE_URL=http://127.0.0.1:8080/proxy/rollout/.../openai/v1
export AGL_EVENT_URL=http://127.0.0.1:8080/api/rollouts/.../events
export AGL_KEY=...
export EIW_AGL_CASE_JSON='{"case_id":"x","question":"Why did sales change?"}'
python scripts/run_agent_lightning_retail_rollout.py
```

The rollout posts an `eiw_metrics` event and one scalar `reward` event built from
semantic coverage, driver recall, action coverage and task completion.

Export fixed + rolling Retail evaluation cases:

```bash
python scripts/export_agent_lightning_retail_cases.py
```

For full GRPO training install:

```bash
pip install -e '.[agent-lightning]'
```

Then use Agent Lightning's server/controller/VERL trainer. The repository does
not claim live RL gains until a GPU-backed training run has produced a preserved
artifact.
