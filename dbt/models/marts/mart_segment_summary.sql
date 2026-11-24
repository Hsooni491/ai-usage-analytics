-- Q7: How do students and professionals differ across job family, education and age?
{% set dims = ['profession_category', 'education_level', 'age_group', 'gender'] %}
{% for d in dims %}
select
    '{{ d }}'          as segment_type,
    {{ d }}            as segment_value,
    user_type,
    {{ kpi_metrics() }}
from {{ ref('fct_ai_usage') }}
group by {{ d }}, user_type
{% if not loop.last %}union all{% endif %}
{% endfor %}
