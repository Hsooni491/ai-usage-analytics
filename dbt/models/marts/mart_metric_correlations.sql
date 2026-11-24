-- Q8: Which numeric drivers move together? (Pearson r, long format for a heat-map)
{% set metrics = ['ai_usage_hours_per_day', 'time_saved_hours_per_week', 'productivity_score',
                  'satisfaction_score', 'accuracy_rating', 'monthly_ai_cost', 'num_tasks',
                  'work_or_study_hours_per_day', 'age'] %}
{% for x in metrics %}{% for y in metrics %}
select
    '{{ x }}' as metric_x,
    '{{ y }}' as metric_y,
    round(corr(cast({{ x }} as double), cast({{ y }} as double)), 3) as pearson_r,
    count({{ x }} + {{ y }}) as n_pairs
from {{ ref('fct_ai_usage') }}
{% if not loop.last %}union all{% endif %}
{% endfor %}{% if not loop.last %}union all{% endif %}
{% endfor %}
