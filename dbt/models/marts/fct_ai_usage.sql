-- Row-level fact: one row per user with every attribute and metric.
-- Main data source for Tableau (lets analysts slice freely).
select * from {{ ref('int_ai_usage_enriched') }}
