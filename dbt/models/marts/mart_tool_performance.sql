-- Q1/Q2: Which AI tools are most used, and which deliver the best results?
with f as (select * from {{ ref('fct_ai_usage') }}),
total as (select count(*) as n from f)

select
    ai_tool,
    {{ kpi_metrics() }},
    round(100.0 * count(*) / max(total.n), 1)                   as pct_of_users,
    sum(case when user_type = 'Student' then 1 else 0 end)      as students,
    sum(case when user_type = 'Professional' then 1 else 0 end) as professionals,
    round(avg(case when monthly_ai_cost > 0 then monthly_ai_cost end), 2) as avg_cost_paid_users,
    rank() over (order by count(*) desc)                        as popularity_rank,
    rank() over (order by avg(satisfaction_score) desc)         as satisfaction_rank
from f cross join total
group by ai_tool
