"""Unit tests for the PySpark bronze -> silver cleaning rules."""

from pathlib import Path

import pytest

from ai_usage_pipeline import add_ingestion_metadata, bronze_to_silver, read_raw_csv
from ai_usage_pipeline.transforms import RAW_COLUMNS

RAW_CSV = Path(__file__).resolve().parents[1] / "data" / "raw" / "ai_usage_raw.csv"


def make_bronze(spark, rows):
    """Build a bronze DataFrame from partial dicts (missing fields are NULL)."""
    data = [tuple(r.get(c) for c in RAW_COLUMNS) for r in rows]
    df = spark.createDataFrame(data, schema=", ".join(f"{c} string" for c in RAW_COLUMNS))
    return add_ingestion_metadata(df, "test.csv")


def silver_row(spark, **fields):
    fields.setdefault("User_ID", "u0001")
    return bronze_to_silver(make_bronze(spark, [fields])).collect()[0]


@pytest.mark.parametrize(
    "column, raw, expected",
    [
        ("AI_Usage_Hours_Per_Day", "2 hrs", 2.0),
        ("AI_Usage_Hours_Per_Day", " 1.7 hrs ", 1.7),
        ("Monthly_Income", "$1,884", 1884.0),
        ("Monthly_AI_Cost", "$20 ", 20.0),
        ("Time_Saved_Hours_Per_Week", "", None),
    ],
)
def test_parses_dirty_numbers(spark, column, raw, expected):
    row = silver_row(spark, **{column: raw})
    assert row[column.lower()] == expected


def test_parses_age_with_unit(spark):
    assert silver_row(spark, Age="28 yrs").age == 28


@pytest.mark.parametrize(
    "column, raw, expected",
    [
        ("AI_Tool", "Chat GPT", "ChatGPT"),
        ("AI_Tool", "chatgpt", "ChatGPT"),
        ("AI_Tool", "copilot", "Microsoft Copilot"),
        ("AI_Tool", "gemini", "Google Gemini"),
        ("AI_Tool", "", "Unknown"),
        ("Gender", "M", "Male"),
        ("Gender", "FEMALE", "Female"),
        ("Gender", None, "Unknown"),
        ("Country", "U.K.", "United Kingdom"),
        ("Country", "United States of America", "United States"),
        ("Country", "brazil", "Brazil"),
        ("Country", "", "Unknown"),
        ("Education_Level", "BA/BSc", "Bachelor's"),
        ("Education_Level", "Ph.D.", "PhD"),
        ("Education_Level", "HS", "High School"),
        ("Would_Recommend", "", "Unknown"),
    ],
)
def test_standardises_categories(spark, column, raw, expected):
    assert silver_row(spark, **{column: raw})[column.lower()] == expected


def test_nulls_and_flags_outliers(spark):
    row = silver_row(spark, Age="97", AI_Usage_Hours_Per_Day="23", Monthly_Income="250000")
    assert row.age is None and row.dq_age_out_of_range
    assert row.ai_usage_hours_per_day is None and row.dq_ai_usage_hours_per_day_out_of_range
    assert row.monthly_income is None and row.dq_monthly_income_out_of_range
    assert row.dq_issue_count >= 3


def test_valid_values_are_not_flagged(spark):
    row = silver_row(spark, Age="30", AI_Tool="Claude", AI_Purpose="Coding", Productivity_Score="7",
                     Satisfaction_Score="8", Monthly_AI_Cost="20", AI_Usage_Hours_Per_Day="3")
    assert row.age == 30
    assert row.dq_issue_count == 0


def test_counts_tasks(spark):
    assert silver_row(spark, Tasks_Performed="write code, review PRs ,  test").num_tasks == 3
    assert silver_row(spark, Tasks_Performed="").num_tasks is None


def test_removes_exact_duplicates(spark):
    rows = [{"User_ID": "U1", "Age": "20"}, {"User_ID": "U1", "Age": "20"}, {"User_ID": "U2", "Age": "30"}]
    assert bronze_to_silver(make_bronze(spark, rows)).count() == 2


def test_full_raw_file(spark):
    bronze = add_ingestion_metadata(read_raw_csv(spark, str(RAW_CSV)), RAW_CSV.name)
    silver = bronze_to_silver(bronze)
    assert bronze.count() == 300
    assert silver.count() == 288
    assert silver.select("user_id").distinct().count() == 288
    tools = {r.ai_tool for r in silver.select("ai_tool").distinct().collect()}
    assert tools <= {"ChatGPT", "Google Gemini", "Microsoft Copilot", "Claude", "Perplexity AI",
                     "Grammarly", "Meta AI", "DeepSeek", "Unknown"}
