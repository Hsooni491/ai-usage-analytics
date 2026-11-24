-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 00 · Setup Unity Catalog objects
-- MAGIC Creates the catalog, the medallion schemas and a Volume for the raw CSV.
-- MAGIC After running this, upload `data/raw/ai_usage_raw.csv` to
-- MAGIC `/Volumes/ai_usage/raw/landing/` (Catalog Explorer → Volume → Upload).

-- COMMAND ----------

CREATE CATALOG IF NOT EXISTS ai_usage;
USE CATALOG ai_usage;

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS raw    COMMENT 'Landing zone (files)';
CREATE SCHEMA IF NOT EXISTS bronze COMMENT 'Raw data as Delta, all strings';
CREATE SCHEMA IF NOT EXISTS silver COMMENT 'Cleaned, typed, de-duplicated';
CREATE SCHEMA IF NOT EXISTS staging COMMENT 'dbt helper views (staging + intermediate)';
CREATE SCHEMA IF NOT EXISTS gold    COMMENT 'dbt fact and mart tables for Tableau';

-- COMMAND ----------

CREATE VOLUME IF NOT EXISTS raw.landing COMMENT 'Drop CSV files here';
