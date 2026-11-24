{# Division that returns NULL instead of failing / dividing by zero. Works on Spark SQL and DuckDB. #}
{% macro safe_divide(numerator, denominator) -%}
    case when ({{ denominator }}) is null or ({{ denominator }}) = 0 then null
         else cast({{ numerator }} as double) / ({{ denominator }}) end
{%- endmacro %}
