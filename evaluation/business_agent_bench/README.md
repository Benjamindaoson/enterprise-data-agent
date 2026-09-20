# BusinessAgentBench

BusinessAgentBench has two complementary suites.

## Hard-v1

A controlled long-horizon decision environment testing:

- partial observability;
- noisy and conflicting evidence;
- deterministic tool failure / timeout;
- delayed reward;
- tool and token budget trade-offs;
- memory dependence;
- context drift;
- unsafe writes and approval gates;
- multiple valid evidence paths;
- retry and replanning.

Run:

```bash
python scripts/run_business_agent_benchmark.py --cases 64
```

## RealData-v1

Grounds business tasks in official public datasets without committing raw source
records into the repository.

- UCI Bank Marketing — campaign / conversion / sales prioritization.
- UCI Online Retail — transactions / retention / monetization.
- Existing Iowa wholesale snapshot — analytics / attribution.

Run:

```bash
pip install -e '.[benchmark]'
python scripts/build_real_business_benchmark.py
```

Use `--bank-only` for the lightweight campaign/conversion profile.
