-- Every user must be counted once: tool shares add up to 100 %.
select sum(pct_of_users) as total_pct
from {{ ref('mart_tool_performance') }}
having abs(sum(pct_of_users) - 100) > 0.5
