-- Q3: For which purposes does AI save the most time — for students vs professionals?
select
    ai_purpose,
    user_type,
    {{ kpi_metrics() }}
from {{ ref('fct_ai_usage') }}
group by ai_purpose, user_type
