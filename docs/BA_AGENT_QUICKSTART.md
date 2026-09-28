# BA Agent quick start

This branch runs a production-shaped, first-party Retail Business Analysis
Agent. The previous OSS bootstrap source trees have been removed after
first-party replacement and benchmark parity.

## 1. Clone

```bash
git clone https://github.com/Benjamindaoson/enterprise-data-agent.git
cd enterprise-data-agent
git checkout feat/retail-ba-agent-v1
```

## 2. Run the first-party BA Agent

No model API or GPU is required for the deterministic product demo.

```bash
python -m pip install -e '.[dev]'
python -m uvicorn eiw.app:app --reload
```

Open:

- BA Agent: http://127.0.0.1:8000/ba
- API docs: http://127.0.0.1:8000/docs
- Retail status: http://127.0.0.1:8000/api/v1/ba/retail/status

The default dataset is an intentionally deterministic CI fixture. The UI and
API label it as such.

## 3. Download the public CC0 Complete Journey data automatically

The open-source `completejourney` package declares the dataset distribution as
CC0 and publishes the full transaction and promotion tables in its GitHub
repository. The ingestion command pins the upstream commit, downloads the R
data files, records SHA-256 hashes, verifies the two published full-table row
counts, and converts all eight package tables to compressed Parquet.

```bash
python -m pip install -e '.[dev,retail-data]'
python scripts/fetch_completejourney_cc0.py data/retail
export EIW_RETAIL_DATA_DIR=$PWD/data/retail
python -m uvicorn eiw.app:app --reload
```

Expected verified core rows from that pinned distribution:

- `transactions`: 1,469,307
- `promotions`: 20,940,529

The generated `completejourney-manifest.json` records actual row counts,
columns, source URLs, source hashes and Parquet hashes for every table.

The runtime also remains compatible with the original dunnhumby source-file
schema (`transaction_data.csv`, `product.csv`, `causal_data.csv`). For
that variant, use:

```bash
python scripts/prepare_complete_journey.py /path/to/raw /path/to/retail
```

## 4. Run the BA benchmark

```bash
python scripts/run_retail_benchmark.py --assert-smoke
```

For local scale measurements on real data:

```bash
python scripts/benchmark_retail_scale.py /path/to/retail --requests 20 --concurrency 4
```

Only locally measured values should be published in README or resume claims.

## 5. Run the first-party Docker stack

```bash
RETAIL_DATA_DIR=$PWD/data/retail \
docker compose -f docker-compose.ba.yml up --build
```

BA Agent: http://localhost:8000/ba

For an optional local OpenAI-compatible model sidecar, set
`LOCAL_MODEL_DIR` and start the `local-model` profile. Point
`EIW_RETAIL_SUPERVISOR_URL` and/or `EIW_RETAIL_CODE_MODEL_URL` to
`http://model-gateway:8000/v1`.

## 6. Optional model-driven Supervisor

The benchmarked default planner is deterministic. To let a real
OpenAI-compatible model choose the first specialist wave and re-plan after
typed intermediate observations, configure:

```bash
export EIW_RETAIL_SUPERVISOR_URL=http://127.0.0.1:8001/v1
export EIW_RETAIL_SUPERVISOR_MODEL=qwen3
export EIW_RETAIL_SUPERVISOR_API_KEY=
python -m uvicorn eiw.app:app --reload
```

The Supervisor only returns a bounded public decision:

```json
{"workstreams":["product","promotion"],"rationale":"short public rationale"}
```

The allowlist is enforced, already-completed workstreams are removed during
re-planning, and any model/API failure automatically falls back to the
deterministic planner. No hidden chain-of-thought is stored or exposed.

## 7. Optional model-backed specialist Agents

The Supervisor chooses **which analyst should work**. A second optional model
policy can let each specialist independently choose **which bounded analytical
skills to use** inside its domain:

```bash
export EIW_RETAIL_SPECIALIST_URL=http://127.0.0.1:8001/v1
export EIW_RETAIL_SPECIALIST_MODEL=qwen3
export EIW_RETAIL_SPECIALIST_API_KEY=
```

Examples of specialist allowlists:

- Store Agent: contribution / anomaly / store×commodity scan;
- Product Agent: commodity contribution / price-volume decomposition;
- Customer Agent: customer concentration / basket affinity / demographics /
  coupon funnel.

The specialist model returns only an allowlisted `skills + rationale` object.
SQL and calculations remain deterministic. Model/API failure automatically
falls back to the full verified deterministic skill set. Completed-workstream
events expose `policy_source`, `selected_skills` and the short public
rationale.

## 8. Stateful interactive drill-down

Every analysis response has a `task_id`. A follow-up can reference it and
carry an explicit business focus while preserving the original period window:

```json
{
  "question": "Continue into store 429 and explain the category drivers.",
  "parent_task_id": "retail-...",
  "focus": {"store": "429"}
}
```

The web demo uses this path when a user clicks **继续调查** or clicks a chart
element. Store focus drills to commodities; commodity/product focus drills to
stores, and the resulting focused insight/chart is placed first.

## 9. First-party AI Coding worker

The preferred open-ended analysis path is now first-party. Point it at any
OpenAI-compatible model endpoint:

```bash
export EIW_RETAIL_CODE_MODEL_URL=http://127.0.0.1:8001/v1
export EIW_RETAIL_CODE_MODEL=qwen3
export EIW_RETAIL_CODE_MODEL_API_KEY=
```

The model receives only a bounded analytical snapshot schema plus a few sample
rows and returns a public `code + explanation` object. The generated code runs
inside the repository-owned Docker sandbox with:

- network disabled;
- read-only root filesystem;
- dropped Linux capabilities;
- `no-new-privileges`;
- memory, CPU and PID limits;
- only the bounded CSV mounted read-only;
- a JSON-serializable `result` output contract.

The endpoint remains:

```text
POST /api/v1/ba/retail/code-analysis
```

When `EIW_RETAIL_CODE_MODEL_URL` is configured, this first-party path takes
priority. The current Docker sandbox launcher is intended for a host-run BA API
(or CI runner) with access to a Docker daemon. The default containerized BA API
does **not** mount the host Docker socket; this avoids turning the application
container into a privileged container-management surface.

## 10. Optional external DeepAnalyze fallback

If an independently operated DeepAnalyze API already exists, it can be used as
a compatibility fallback:

```bash
export EIW_DEEPANALYZE_URL=http://127.0.0.1:8200/v1
```

No DeepAnalyze source is vendored by this repository. The first-party
`EIW_RETAIL_CODE_MODEL_URL` path takes precedence.

## 11. OSS bootstrap history

See `THIRD_PARTY_NOTICES.md` and `docs/UPSTREAM_BOOTSTRAP.md`. The product
runtime is now first-party; these files only record the bootstrap/reference
history.

