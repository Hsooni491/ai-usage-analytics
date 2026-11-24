-- =====================================================================
-- Business questions answered from the gold layer.
-- Runs on Databricks SQL (USE CATALOG ai_usage) and on the local DuckDB file.
-- =====================================================================
-- USE CATALOG ai_usage;   -- Databricks only

-- Q1. Which AI tools are most popular, and with whom?
SELECT ai_tool, users, pct_of_users, students, professionals
FROM gold.mart_tool_performance
WHERE ai_tool <> 'Unknown'
ORDER BY users DESC;

-- Q2. Which tool delivers the best experience (min. 10 users)?
SELECT ai_tool, users, avg_productivity, avg_satisfaction, avg_accuracy,
       recommend_yes_pct, net_recommend_score
FROM gold.mart_tool_performance
WHERE ai_tool <> 'Unknown' AND users >= 10
ORDER BY net_recommend_score DESC;

-- Q3. For which purposes does AI save the most time?
SELECT ai_purpose, user_type, users, avg_time_saved_hrs_week, avg_productivity
FROM gold.mart_purpose_impact
WHERE ai_purpose <> 'Unknown'
ORDER BY avg_time_saved_hrs_week DESC;

-- Q4. Does more daily AI usage mean more productivity and time saved?
SELECT usage_band,
       SUM(users)                                                         AS users,
       ROUND(SUM(avg_productivity * users) / SUM(users), 2)               AS avg_productivity,
       ROUND(SUM(avg_time_saved_hrs_week * users) / SUM(users), 2)        AS avg_time_saved_hrs_week,
       ROUND(SUM(avg_satisfaction * users) / SUM(users), 2)               AS avg_satisfaction
FROM gold.mart_usage_intensity
WHERE usage_band <> 'Unknown'
GROUP BY usage_band, usage_band_order
ORDER BY usage_band_order;

-- Q5. Do paying users get more value than free users?
SELECT plan_tier, user_type, users, avg_productivity, avg_satisfaction,
       avg_time_saved_hrs_week, avg_monthly_cost, median_cost_per_hour_saved
FROM gold.mart_plan_tier_value
WHERE plan_tier <> 'Unknown'
ORDER BY user_type, avg_monthly_cost;

-- Q6. How does adoption differ by country?
SELECT country, users, avg_productivity, avg_satisfaction, pct_paid_users, top_ai_tool
FROM gold.mart_country_summary
WHERE country <> 'Unknown'
ORDER BY users DESC;

-- Q7. Students vs professionals: which job families benefit most?
SELECT segment_value AS profession_category, user_type, users,
       avg_productivity, avg_time_saved_hrs_week, avg_satisfaction
FROM gold.mart_segment_summary
WHERE segment_type = 'profession_category' AND segment_value <> 'Unknown'
ORDER BY avg_time_saved_hrs_week DESC;

-- Q8. Which metrics move together most strongly?
SELECT metric_x, metric_y, pearson_r, n_pairs
FROM gold.mart_metric_correlations
WHERE metric_x < metric_y
ORDER BY ABS(pearson_r) DESC
LIMIT 10;

-- Q9. How clean was the raw data?
SELECT check_name, check_type, affected_rows, total_rows,
       ROUND(100.0 * affected_rows / total_rows, 1) AS pct_affected
FROM gold.mart_data_quality
ORDER BY affected_rows DESC;
