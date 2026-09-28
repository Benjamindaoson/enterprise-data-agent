# BA Agent quick start

This branch runs a production-shaped retail BA Agent while keeping large
third-party components isolated behind replaceable boundaries.

## 1. Clone with pinned upstreams

```bash
git clone --recurse-submodules https://github.com/Benjamindaoson/enterprise-data-agent.git
cd enterprise-data-agent
git checkout feat/ba-agent-upstream-bootstrap
git submodule update --init --recursive
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

## 3. Use a real Complete Journey checkout

Obtain the data under its publisher's terms. The repository does not
redistribute it.

Expected source files:

- `transaction_data.csv`
- `product.csv`
- `causal_data.csv`

Optionally convert them to compressed Parquet:

```bash
python scripts/prepare_complete_journey.py /path/to/raw /path/to/retail
export EIW_RETAIL_DATA_DIR=/path/to/retail
python -m uvicorn eiw.app:app --reload
```

The runtime accepts the corresponding `.parquet` files as well.

## 4. Run the BA benchmark

```bash
python scripts/run_retail_benchmark.py --assert-smoke
```

For local scale measurements on real data:

```bash
python scripts/benchmark_retail_scale.py /path/to/retail --requests 20 --concurrency 4
```

Only locally measured values should be published in README or resume claims.

## 5. Start Microsoft Data Formulator alongside BA Agent

```bash
docker compose -f docker-compose.ba.yml --profile upstream-ui up --build
```

- BA Agent: http://localhost:8000/ba
- Data Formulator: http://localhost:5567

To mount real retail data into the container, set both the host mount and the
container path:

```bash
RETAIL_DATA_DIR=/absolute/path/to/retail \
EIW_RETAIL_DATA_DIR=/data/retail \
docker compose -f docker-compose.ba.yml --profile upstream-ui up --build
```

Data Formulator remains a pinned MIT-licensed upstream during bootstrap. Its
Data Thread / visualization / sandbox patterns are being replaced behind
first-party product contracts after parity is established.

## 6. Optional DeepAnalyze code analyst

Download DeepAnalyze-8B separately and set:

```bash
export DEEPANALYZE_MODEL_DIR=/absolute/path/to/DeepAnalyze-8B
docker compose -f docker-compose.ba.yml --profile deepanalyze up --build
```

The stack exposes:

- vLLM: http://localhost:8001/v1
- full DeepAnalyze API (including code execution): http://localhost:8200/v1

To connect a locally started BA API:

```bash
export EIW_DEEPANALYZE_URL=http://127.0.0.1:8200/v1
```

The BA endpoint `POST /api/v1/ba/retail/code-analysis` sends only a bounded
store × commodity snapshot to the optional code analyst.

## 7. Upstream policy

See:

- `THIRD_PARTY_NOTICES.md`
- `docs/UPSTREAM_BOOTSTRAP.md`

The first-party contracts are the product boundary. Upstream code is replaced
one capability at a time only after tests and BA benchmarks show parity or
improvement.
