# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze ingest (PySpark)
# MAGIC Reads the raw CSV from the Unity Catalog Volume with **every column as STRING**
# MAGIC (nothing is lost or coerced), adds lineage columns and writes a Delta table.

# COMMAND ----------

dbutils.widgets.text("catalog", "ai_usage")
dbutils.widgets.text("source_path", "/Volumes/ai_usage/raw/landing/ai_usage_raw.csv")
catalog = dbutils.widgets.get("catalog")
source_path = dbutils.widgets.get("source_path")

# COMMAND ----------

import os
import sys

# Make ../../src importable when this repo is a Databricks Git folder
repo_root = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))
sys.path.insert(0, os.path.join(repo_root, "src"))

from ai_usage_pipeline import read_raw_csv, add_ingestion_metadata

# COMMAND ----------

bronze = add_ingestion_metadata(read_raw_csv(spark, source_path), os.path.basename(source_path))

(bronze.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.bronze.ai_usage_raw"))

display(spark.sql(f"SELECT COUNT(*) AS bronze_rows FROM {catalog}.bronze.ai_usage_raw"))
