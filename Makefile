.PHONY: setup data test lint dev evaluation

setup:
	python -m pip install -e '.[dev,postgres]'

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
