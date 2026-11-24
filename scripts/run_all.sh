#!/usr/bin/env bash
# Full local pipeline: PySpark bronze/silver -> dbt gold (+ data tests) on DuckDB
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
DBT="${DBT:-$ROOT/.venv/bin/dbt}"
export LAKE_PATH="$ROOT/data/lake"

echo "==> 1/2 PySpark: bronze + silver"
"$PY" "$ROOT/scripts/run_local.py"

echo "==> 2/2 dbt: build gold models and run tests"
(cd "$ROOT/dbt" && "$DBT" build --profiles-dir .)
