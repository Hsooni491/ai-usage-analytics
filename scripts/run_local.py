"""
Run the Bronze -> Silver PySpark layers locally (no Databricks needed).

Writes Parquet to data/lake/{bronze,silver}/ which the local dbt target (DuckDB)
reads as its source. On Databricks the same transforms write Delta tables instead.

    python scripts/run_local.py
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# Spark workers must use the same interpreter as the driver
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)

from pyspark.sql import SparkSession  # noqa: E402

from ai_usage_pipeline import add_ingestion_metadata, bronze_to_silver, read_raw_csv  # noqa: E402

RAW = ROOT / "data" / "raw" / "ai_usage_raw.csv"
LAKE = ROOT / "data" / "lake"


def main() -> None:
    spark = (
        SparkSession.builder.appName("ai_usage_local")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    # Bronze
    bronze = add_ingestion_metadata(read_raw_csv(spark, str(RAW)), RAW.name)
    bronze_path = LAKE / "bronze" / "ai_usage_raw"
    shutil.rmtree(bronze_path, ignore_errors=True)
    bronze.coalesce(1).write.mode("overwrite").parquet(str(bronze_path))
    bronze = spark.read.parquet(str(bronze_path))

    # Silver
    silver = bronze_to_silver(bronze)
    silver_path = LAKE / "silver" / "ai_usage_clean"
    shutil.rmtree(silver_path, ignore_errors=True)
    silver.coalesce(1).write.mode("overwrite").parquet(str(silver_path))
    silver = spark.read.parquet(str(silver_path))

    print(f"bronze rows : {bronze.count()}")
    print(f"silver rows : {silver.count()}  (after de-duplication)")
    print("rows with >=1 data-quality issue:", silver.filter("dq_issue_count > 0").count())
    silver.groupBy("ai_tool").count().orderBy("count", ascending=False).show(truncate=False)
    spark.stop()


if __name__ == "__main__":
    main()
