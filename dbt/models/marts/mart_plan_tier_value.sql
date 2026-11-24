-- Q5: Are paying users more productive / satisfied than free users? What does an hour saved cost?
select
    plan_tier,
    user_type,
    {{ kpi_metrics() }},
    round(avg(monthly_ai_cost), 2)        as avg_monthly_cost,
    round(median(cost_per_hour_saved), 2) as median_cost_per_hour_saved
from {{ ref('fct_ai_usage') }}
group by plan_tier, user_type
