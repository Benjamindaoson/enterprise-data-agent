# Semantic Evolution Evidence

This document records the current reproducible evidence for the enterprise ontology layer. It distinguishes **mechanism tests**, **blind real-data evidence**, and **credentialed live-model evidence** so the repository does not overclaim unexecuted results.

## 1. Four-way blind onboarding ablation

Workflow run: `36507597993`  
Artifact: `blind-ontology-benchmark` / artifact id `11008115294`  
Benchmark: `BlindEnterpriseOntologyBench-v1`

The benchmark loads **25,000 rows** from the public UCI Online Retail dataset into a previously unseen PostgreSQL schema. Gold semantics are used only for held-out scoring and are **not exposed to the ontology builder**.

Compared lanes:

1. Raw schema
2. Static inferred semantic package
3. Initial evidence-grounded ontology
4. Evolved ontology after workload failure mining + paired promotion gate

Held-out questions cover revenue, units, average selling price, active customers, unsupported gross margin, and a paraphrased units-by-country request.

| Lane | Semantic Coverage | Task Success | Numeric Accuracy | Correct Abstention | Tool Calls | Turns | P95 Latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw schema | 0.1667 | 0.1667 | 0.1667 | 1.0000 | 1.000 | 1.000 | 0.027 |
| Static semantic package | 0.1667 | 0.1667 | 0.1667 | 1.0000 | 1.000 | 1.000 | 0.024 |
| Initial ontology | 0.1667 | 0.1667 | 0.1667 | 1.0000 | 2.000 | 2.000 | 0.150 |
| **Evolved ontology** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | 2.833 | 2.833 | 81.069 |

The paired gate compared the initial ontology with the evolved candidate on the same evaluation path:

- baseline quality: **0.166667**
- candidate quality: **1.000000**
- quality gain: **+0.833333**
- security resistance: **1.000 → 1.000**
- permission compliance: **1.000 → 1.000**
- causal discipline: **1.000 → 1.000**
- promotion: **PASS**

This is evidence that the implemented evolution path improves the benchmarked blind-onboarding workload. It is **not** a claim that arbitrary enterprise schemas will reach perfect performance.

## 2. Model-driven semantic builder

Implementation:

- `ModelDrivenPostgresOntologyBuilder`
- `OpenAIResponsesSemanticBuilderModel`
- `ModelSemanticPlan`
- `ontology_to_postgres_semantic_package`

The model is allowed to propose business concepts such as Revenue, Active Customer, Conversion Rate, and derived metrics, but every physical table/column reference is validated against the governed catalog before an ontology state can be committed.

Current contract tests verify:

- executable derived metrics such as `Quantity * UnitPrice`;
- count-distinct and rate-style metric contracts;
- unsupported business concepts are represented as hard constraints rather than fabricated fields;
- hallucinated physical columns are rejected;
- Responses API payload parsing is typed;
- credentials are runtime-only and never persisted in repository artifacts.

The live entry point is:

```bash
EIW_ONTOLOGY_MODEL_API_KEY=... \
EIW_ONTOLOGY_MODEL=<model> \
EIW_TEST_DATABASE_URL=postgresql+psycopg://... \
python scripts/run_live_model_ontology_builder.py --require-live
```

A manual GitHub Actions workflow is also provided so a repository secret can be used without committing credentials.

## 3. Blind-schema onboarding

The blind benchmark intentionally withholds the manually authored gold semantic package from the builder.

Pipeline:

```text
Unseen PostgreSQL schema
        ↓
catalog introspection
        ↓
safe aggregate-only probes
        ↓
initial ontology
        ↓
adaptation workload
        ↓
failure mining
        ↓
bounded semantic patch
        ↓
paired enterprise gate
        ↓
held-out questions
        ↓
compare against hidden gold semantics
```

The real-data benchmark runs inside the PostgreSQL 16 production-integration CI job and uploads the exact JSON evidence artifact.

## 4. CI baseline

Verified on main workflow run `36507597993`:

- core: PASS
- post-training-smoke: PASS
- real-data-benchmark: PASS
- production-integration: PASS
- production/integration subset: **11 passed**
- blind ontology ablation: PASS and artifact uploaded

## Claim boundary

Safe claim:

> On a blind UCI Online Retail PostgreSQL onboarding benchmark, the evolved ontology improved held-out semantic coverage, task success, and numeric accuracy from 0.1667 to 1.0 while preserving perfect abstention, security, permission, and causal-discipline gates.

Do not claim:

- universal enterprise-schema performance;
- external state of the art;
- a live-provider gain unless a credentialed live-model workflow has actually run and its artifact is preserved.
