# Common tasks. Run `make help` to list them.
PY      ?= .venv/bin/python
DBT     ?= $(CURDIR)/.venv/bin/dbt
PROFILE ?= ai-usage
TARGET  ?= dev

.PHONY: help setup lint test pipeline dbt-docs deploy run-job clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

PYTHON_BIN ?= python3.12

setup:  ## Create .venv (Python 3.10-3.12) and install dependencies
	$(PYTHON_BIN) -m venv .venv
	$(PY) -m pip install -U pip
	$(PY) -m pip install -r requirements-dev.txt

lint:  ## Lint Python code
	$(PY) -m ruff check .

test:  ## Run unit tests
	$(PY) -m pytest

pipeline:  ## Run the full local pipeline: PySpark -> dbt (DuckDB) -> Tableau files
	PYTHON=$(PY) DBT=$(DBT) ./scripts/run_all.sh

dbt-docs:  ## Generate and serve dbt documentation (lineage graph) locally
	cd dbt && LAKE_PATH=$(CURDIR)/data/lake $(DBT) docs generate --profiles-dir . && $(DBT) docs serve --profiles-dir .

deploy:  ## Deploy the Databricks bundle (job + notebooks + dbt project)
	databricks bundle deploy -t $(TARGET) --profile $(PROFILE)

run-job:  ## Run the pipeline job on Databricks
	databricks bundle run ai_usage_pipeline -t $(TARGET) --profile $(PROFILE)

clean:  ## Remove generated local artefacts
	rm -rf data/lake dbt/target dbt/logs dbt/*.duckdb .pytest_cache .ruff_cache
