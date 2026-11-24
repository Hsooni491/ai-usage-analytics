-- Pipeline health: what the PySpark silver layer fixed or flagged.
{% set flags = ['age_out_of_range', 'monthly_income_out_of_range', 'ai_usage_hours_per_day_out_of_range',
                'work_or_study_hours_per_day_out_of_range', 'time_saved_hours_per_week_out_of_range',
                'monthly_ai_cost_out_of_range', 'age_missing', 'ai_tool_missing', 'ai_purpose_missing',
                'productivity_score_missing', 'satisfaction_score_missing', 'monthly_ai_cost_missing'] %}
with silver as (select * from {{ source('silver', 'ai_usage_clean') }}),
     bronze as (select count(*) as n from {{ source('bronze', 'ai_usage_raw') }})

select 'duplicate_rows_removed' as check_name, 'dedup' as check_type,
       (select n from bronze) - (select count(*) from silver) as affected_rows,
       (select n from bronze) as total_rows
{% for f in flags %}
union all
select '{{ f }}',
       case when '{{ f }}' like '%missing' then 'missing' else 'outlier_nulled' end,
       sum(cast(dq_{{ f }} as int)),
       count(*)
from silver
{% endfor %}
