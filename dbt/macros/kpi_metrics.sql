{# Standard KPI block reused by every aggregate mart (keeps definitions consistent). #}
{% macro kpi_metrics() -%}
    count(*)                                                    as users,
    round(avg(productivity_score), 2)                           as avg_productivity,
    round(avg(satisfaction_score), 2)                           as avg_satisfaction,
    round(avg(accuracy_rating), 2)                              as avg_accuracy,
    round(avg(time_saved_hours_per_week), 2)                    as avg_time_saved_hrs_week,
    round(avg(ai_usage_hours_per_day), 2)                       as avg_ai_hours_day,
    round(avg(hours_saved_per_ai_hour), 3)                      as avg_hours_saved_per_ai_hour,
    round(100.0 * sum(is_paid_user) / count(*), 1)              as pct_paid_users,
    round(100.0 * sum(is_promoter) / count(*), 1)               as recommend_yes_pct,
    round(100.0 * (sum(is_promoter) - sum(is_detractor)) / count(*), 1) as net_recommend_score
{%- endmacro %}
