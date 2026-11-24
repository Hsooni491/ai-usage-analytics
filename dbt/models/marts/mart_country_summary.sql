-- Q6: AI adoption and outcomes by country, including each country's most-used tool.
with f as (select * from {{ ref('fct_ai_usage') }}),

tool_rank as (
    select
        country, ai_tool,
        row_number() over (partition by country order by count(*) desc, ai_tool) as rn
    from f
    where ai_tool <> 'Unknown'
    group by country, ai_tool
)

select
    f.country,
    {{ kpi_metrics() }},
    round(avg(f.monthly_income), 0) as avg_monthly_income,
    max(t.ai_tool)                  as top_ai_tool
from f
left join tool_rank t on t.country = f.country and t.rn = 1
group by f.country
