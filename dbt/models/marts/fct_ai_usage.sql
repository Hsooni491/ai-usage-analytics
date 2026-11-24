-- Row-level fact: one row per user with every attribute and metric.
-- Main data source for the AI/BI dashboard (lets analysts slice freely).
select * from {{ ref('int_ai_usage_enriched') }}
