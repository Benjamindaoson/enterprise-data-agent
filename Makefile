.PHONY: setup setup-training data test lint dev evaluation trajectories train-sft train-grpo flywheel-smoke

setup:
	python -m pip install -e '.[dev,postgres]'

setup-training:
	python -m pip install -e '.[dev,training]'

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
