-- Q4: Does using AI more hours per day pay off (productivity, time saved, satisfaction)?
select
    usage_band,
    usage_band_order,
    user_type,
    {{ kpi_metrics() }}
from {{ ref('fct_ai_usage') }}
group by usage_band, usage_band_order, user_type
