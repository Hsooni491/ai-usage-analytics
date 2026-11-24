"""
Export the dbt gold layer to CSV files for Tableau (local / Tableau Public workflow).

On Databricks you don't need this: connect Tableau directly to the SQL warehouse
(Connect → Databricks) and pick tables from catalog `ai_usage`, schema `gold`.

    python scripts/export_for_tableau.py
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "dbt" / "ai_usage.duckdb"
OUT = ROOT / "tableau" / "data"
OUT.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(DB), read_only=True)
tables = [r[0] for r in con.sql(
    "select table_name from information_schema.tables "
    "where table_schema = 'gold' and table_type = 'BASE TABLE' order by 1").fetchall()]

# Run-time lineage columns change on every run; leave them out so exports are reproducible
VOLATILE = {"processed_at"}

for t in tables:
    path = OUT / f"{t}.csv"
    cols = [r[0] for r in con.sql(f"select * from gold.{t} limit 0").description]
    keep = ", ".join(f'"{c}"' for c in cols if c not in VOLATILE)
    con.execute(f"copy (select {keep} from gold.{t} order by all) to '{path}' (header, delimiter ',')")
    n = con.sql(f"select count(*) from gold.{t}").fetchall()[0][0]
    print(f"{t:<28} {n:>5} rows -> {path.relative_to(ROOT)}")
