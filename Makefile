.PHONY: setup download quality mart train evaluate test run-api run-app compose-up compose-down clean

setup:
	pip install -e .
	pip install -e ".[dev]"

download:
	python -m smart_replenishment.data.ingest

quality:
	python -m smart_replenishment.data.quality

mart:
	python -m smart_replenishment.data.mart

pipeline: download quality mart

test:
	pytest tests/

run-api:
	uvicorn smart_replenishment.api.main:app --host 0.0.0.0 --port 8000 --reload

run-app:
	streamlit run src/smart_replenishment/dashboard/app.py

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
