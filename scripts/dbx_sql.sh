#!/usr/bin/env bash
# Run one SQL statement on a Databricks SQL warehouse through the CLI.
#   scripts/dbx_sql.sh "<sql>"     (env: DBX_PROFILE, DBX_WAREHOUSE_ID)
set -euo pipefail
SQL="$1"
BODY=$(python3 -c 'import json,sys,os;print(json.dumps({"warehouse_id":os.environ["DBX_WAREHOUSE_ID"],"statement":sys.argv[1],"wait_timeout":"50s","format":"JSON_ARRAY","disposition":"INLINE"}))' "$SQL")
databricks api post /api/2.0/sql/statements --profile "${DBX_PROFILE:-ai-usage}" --json "$BODY" \
 | python3 -c '
import json,sys
d=json.load(sys.stdin); s=d["status"]
if s["state"]!="SUCCEEDED": print("STATE",s["state"],s.get("error",{}).get("message","")); sys.exit(1)
cols=[c["name"] for c in d.get("manifest",{}).get("schema",{}).get("columns",[])]
rows=d.get("result",{}).get("data_array",[]) or []
if cols: print(" | ".join(cols))
for r in rows: print(" | ".join("" if v is None else str(v) for v in r))
if not cols: print("OK")'
