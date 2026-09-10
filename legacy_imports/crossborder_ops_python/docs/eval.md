# Eval Set

The eval set lives at:

```text
eval/cases.jsonl
```

Each line contains:

```json
{"id":"summary-zh","question":"分析最近 30 天经营概览","mustContain":["经营概览"]}
```

Run:

```powershell
.\.venv\Scripts\python.exe -m app.eval_runner
```

The current eval is deterministic and uses the seeded SQLite demo database. It verifies routing and required output fragments for:

- business summary;
- trend chart payload;
- refund risk;
- high ACOS/ROAS;
- low-star review insight.

This is not a full LLM quality benchmark. It is a regression guard for the Agent-to-Tool business chain.
