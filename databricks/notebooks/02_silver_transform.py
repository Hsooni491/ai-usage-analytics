# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver transform (PySpark)
# MAGIC * removes the 12 exact duplicate records
# MAGIC * parses dirty numbers (`"2 hrs"`, `"28 yrs"`, `"$1,884"`)
# MAGIC * standardises categories (`Chat GPT`/`chatgpt` → `ChatGPT`, `M`/`MALE` → `Male`, `U.K.` → `United Kingdom` …)
# MAGIC * nulls implausible values (age 97, 23 h/day AI usage, income 250,000) and keeps a `dq_*` flag for each
# MAGIC * derives `num_tasks` from the free-text task list

# COMMAND ----------

dbutils.widgets.text("catalog", "ai_usage")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

import os
import sys
repo_root = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))
sys.path.insert(0, os.path.join(repo_root, "src"))

from ai_usage_pipeline import bronze_to_silver

# COMMAND ----------

bronze = spark.table(f"{catalog}.bronze.ai_usage_raw")
silver = bronze_to_silver(bronze)

(silver.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.silver.ai_usage_clean"))

# COMMAND ----------

# MAGIC %md ### Data-quality summary

# COMMAND ----------

dq_cols = [c for c in silver.columns if c.startswith("dq_") and c != "dq_issue_count"]
spark.sql(f"OPTIMIZE {catalog}.silver.ai_usage_clean")
display(
    spark.table(f"{catalog}.silver.ai_usage_clean")
    .selectExpr(*[f"SUM(CAST({c} AS INT)) AS {c}" for c in dq_cols])
)
