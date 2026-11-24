#!/usr/bin/env bash
# Full local pipeline: PySpark bronze/silver -> dbt gold (+tests) -> Tableau CSVs
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
DBT="${DBT:-$ROOT/.venv/bin/dbt}"
export LAKE_PATH="$ROOT/data/lake"

echo "==> 1/4 PySpark: bronze + silver"
"$PY" "$ROOT/scripts/run_local.py"

echo "==> 2/4 dbt: build gold models and run tests"
(cd "$ROOT/dbt" && "$DBT" build --profiles-dir .)

echo "==> 3/4 Export gold tables for Tableau"
"$PY" "$ROOT/scripts/export_for_tableau.py"

echo "==> 4/4 Build Tableau packaged workbook"
"$PY" "$ROOT/scripts/build_tableau_workbook.py"
