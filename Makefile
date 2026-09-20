.PHONY: setup setup-training setup-llm setup-production data test lint dev evaluation trajectories train-sft train-grpo flywheel-smoke benchmark-hard benchmark-real train-hard llm-dataset llm-sft llm-grpo production-test observability

setup:
	python -m pip install -e '.[dev,postgres]'

setup-training:
	python -m pip install -e '.[dev,training]'

setup-llm:
	python -m pip install -e '.[dev,llm]'

setup-production:
	python -m pip install -e '.[dev,production]'

data:
	python scripts/curate_iowa_snapshot.py

validate-data:
	python scripts/validate_iowa_snapshot.py

test:
	python -m pytest -q

lint:
	python -m ruff check src tests scripts

dev:
	python -m uvicorn eiw.app:app --reload

evaluation:
	python -m pytest tests/contract tests/integration -q


trajectories:
	python scripts/generate_agent_trajectories.py

train-sft: trajectories
	python scripts/train_agent_sft.py

train-grpo: train-sft
	python scripts/train_agent_grpo.py

flywheel-smoke:
	python scripts/generate_agent_trajectories.py --episodes-per-scenario 2
	python scripts/train_agent_sft.py --epochs 8
	python scripts/train_agent_grpo.py --iterations 2 --group-size 3

benchmark-hard:
	python scripts/run_business_agent_benchmark.py --cases 64

benchmark-real:
	python scripts/build_real_business_benchmark.py

train-hard:
	python scripts/train_hard_business_agent.py

llm-dataset:
	python scripts/export_llm_agent_dataset.py

llm-sft: llm-dataset
	python scripts/train_llm_agent_sft.py

llm-grpo: llm-sft
	python scripts/train_llm_agent_grpo.py

production-test:
	python -m pytest tests/unit/test_production_runtime.py tests/integration/test_production_services.py -q

observability:
	docker compose up -d redis otel-collector prometheus grafana
