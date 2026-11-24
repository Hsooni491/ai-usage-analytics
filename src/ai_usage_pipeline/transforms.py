"""
PySpark transformations for the AI Usage pipeline (Bronze -> Silver).

Pure functions: each takes a DataFrame and returns a DataFrame, so the same
code runs in a Databricks notebook and in the local runner (scripts/run_local.py).
"""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T

RAW_COLUMNS = [
    "User_ID", "Age", "Gender", "Country", "User_Type", "Education_Level",
    "Profession", "Monthly_Income", "AI_Tool", "AI_Purpose",
    "AI_Usage_Hours_Per_Day", "Tasks_Performed", "Monthly_AI_Cost",
    "Productivity_Score", "Accuracy_Rating", "Satisfaction_Score",
    "Time_Saved_Hours_Per_Week", "Work_or_Study_Hours_Per_Day", "Would_Recommend",
]

# Plausibility limits. Values outside them are set to NULL and flagged.
LIMITS = {
    "age": (13, 90),
    "monthly_income": (0, 100_000),
    "ai_usage_hours_per_day": (0, 16),
    "work_or_study_hours_per_day": (0, 18),
    "time_saved_hours_per_week": (0, 60),
    "monthly_ai_cost": (0, 1_000),
}

# --------------------------------------------------------------------------- #
# Lookup maps (lower-cased key -> canonical value)
# --------------------------------------------------------------------------- #
GENDER_MAP = {
    "male": "Male", "m": "Male",
    "female": "Female", "f": "Female",
    "other": "Other", "non-binary": "Non-binary",
}
COUNTRY_MAP = {
    "u.k.": "United Kingdom", "uk": "United Kingdom",
    "united states of america": "United States", "usa": "United States",
    "u.s.": "United States", "us": "United States",
}
EDUCATION_MAP = {
    "high school": "High School", "hs": "High School",
    "diploma": "Diploma",
    "undergraduate": "Undergraduate", "undergrad": "Undergraduate",
    "bachelor's": "Bachelor's", "bachelors": "Bachelor's",
    "bachelor's degree": "Bachelor's", "ba/bsc": "Bachelor's",
    "master's": "Master's", "masters": "Master's",
    "master's degree": "Master's", "ma/msc": "Master's",
    "phd": "PhD", "ph.d.": "PhD",
}
AI_TOOL_MAP = {
    "chatgpt": "ChatGPT", "chat gpt": "ChatGPT",
    "gemini": "Google Gemini", "google gemini": "Google Gemini",
    "copilot": "Microsoft Copilot", "microsoft copilot": "Microsoft Copilot",
    "claude": "Claude", "perplexity ai": "Perplexity AI", "perplexity": "Perplexity AI",
    "grammarly": "Grammarly", "meta ai": "Meta AI", "deepseek": "DeepSeek",
}


def _map_col(col: F.Column, mapping: dict, default: F.Column | None = None) -> F.Column:
    """Map lower-cased string values through a dict; fall back to `default`."""
    m = F.create_map(*[F.lit(x) for kv in mapping.items() for x in kv])
    key = F.lower(F.trim(col))
    return F.coalesce(m[key], default if default is not None else F.lit(None))


def _blank_to_null(col: F.Column) -> F.Column:
    c = F.trim(col)
    return F.when((c == "") | c.isNull(), None).otherwise(c)


def _to_number(col: F.Column) -> F.Column:
    """'$1,884' -> 1884.0, '2 hrs' -> 2.0, '28 yrs' -> 28.0, '' -> NULL"""
    cleaned = F.regexp_replace(F.lower(F.trim(col)), r"[\$,]|hrs?|yrs?|\s", "")
    return F.when(cleaned == "", None).otherwise(cleaned.cast(T.DoubleType()))


def _in_range(col_name: str) -> F.Column:
    lo, hi = LIMITS[col_name]
    return F.col(col_name).between(lo, hi)


# --------------------------------------------------------------------------- #
# Bronze
# --------------------------------------------------------------------------- #
def read_raw_csv(spark: SparkSession, path: str) -> DataFrame:
    """Read the CSV with every column as STRING (schema-on-read, nothing lost)."""
    schema = T.StructType([T.StructField(c, T.StringType(), True) for c in RAW_COLUMNS])
    return (
        spark.read.option("header", True)
        .option("multiLine", True)
        .option("escape", '"')
        .option("encoding", "UTF-8")
        .schema(schema)
        .csv(path)
    )


def add_ingestion_metadata(df: DataFrame, source_file: str) -> DataFrame:
    # Hash of every source field, used to detect exact duplicate records
    row_hash = F.sha2(F.concat_ws("||", *[F.coalesce(F.col(c), F.lit("")) for c in RAW_COLUMNS]), 256)
    return (
        df.withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.lit(source_file))
        .withColumn("_row_hash", row_hash)
    )


# --------------------------------------------------------------------------- #
# Silver
# --------------------------------------------------------------------------- #
def deduplicate(df: DataFrame) -> DataFrame:
    """Drop exact duplicate records (same row hash), then keep one row per User_ID."""
    return df.dropDuplicates(["_row_hash"]).dropDuplicates(["User_ID"])


def clean(df: DataFrame) -> DataFrame:
    """Standardise text, parse numbers, null-out implausible values, add DQ flags."""
    out = df.select(
        F.upper(F.trim("User_ID")).alias("user_id"),
        _to_number(F.col("Age")).cast("int").alias("age"),
        _map_col(F.col("Gender"), GENDER_MAP, F.lit("Unknown")).alias("gender"),
        _map_col(
            F.col("Country"), COUNTRY_MAP,
            F.coalesce(F.initcap(_blank_to_null(F.col("Country"))), F.lit("Unknown")),
        ).alias("country"),
        F.initcap(F.trim("User_Type")).alias("user_type"),
        _map_col(F.col("Education_Level"), EDUCATION_MAP, F.lit("Unknown")).alias("education_level"),
        F.coalesce(_blank_to_null(F.col("Profession")), F.lit("Unknown")).alias("profession"),
        _to_number(F.col("Monthly_Income")).alias("monthly_income"),
        _map_col(F.col("AI_Tool"), AI_TOOL_MAP, F.lit("Unknown")).alias("ai_tool"),
        F.coalesce(_blank_to_null(F.col("AI_Purpose")), F.lit("Unknown")).alias("ai_purpose"),
        _to_number(F.col("AI_Usage_Hours_Per_Day")).alias("ai_usage_hours_per_day"),
        _blank_to_null(F.col("Tasks_Performed")).alias("tasks_performed"),
        _to_number(F.col("Monthly_AI_Cost")).alias("monthly_ai_cost"),
        _to_number(F.col("Productivity_Score")).alias("productivity_score"),
        _to_number(F.col("Accuracy_Rating")).cast("int").alias("accuracy_rating"),
        _to_number(F.col("Satisfaction_Score")).cast("int").alias("satisfaction_score"),
        _to_number(F.col("Time_Saved_Hours_Per_Week")).alias("time_saved_hours_per_week"),
        _to_number(F.col("Work_or_Study_Hours_Per_Day")).alias("work_or_study_hours_per_day"),
        F.coalesce(F.initcap(_blank_to_null(F.col("Would_Recommend"))), F.lit("Unknown")).alias("would_recommend"),
        "_ingested_at", "_source_file",
    )

    # Number of tasks listed (comma-separated free text)
    out = out.withColumn(
        "num_tasks",
        F.when(F.col("tasks_performed").isNull(), None)
        .otherwise(F.size(F.split("tasks_performed", r"\s*,\s*"))),
    )

    # Outlier handling: flag, then null-out so averages are not distorted
    for c in LIMITS:
        flag = f"dq_{c}_out_of_range"
        out = out.withColumn(flag, F.col(c).isNotNull() & ~_in_range(c))
        out = out.withColumn(c, F.when(F.col(flag), None).otherwise(F.col(c)))

    # Missing-value flags on the key analytical fields
    for c in ["age", "ai_tool", "ai_purpose", "productivity_score", "satisfaction_score", "monthly_ai_cost"]:
        missing = F.col(c).isNull() | (F.col(c) == "Unknown") if c in ("ai_tool", "ai_purpose") else F.col(c).isNull()
        out = out.withColumn(f"dq_{c}_missing", missing)

    dq_cols = [c for c in out.columns if c.startswith("dq_")]
    out = out.withColumn("dq_issue_count", sum(F.col(c).cast("int") for c in dq_cols))
    return out.withColumn("_processed_at", F.current_timestamp())


def bronze_to_silver(bronze: DataFrame) -> DataFrame:
    return clean(deduplicate(bronze))
