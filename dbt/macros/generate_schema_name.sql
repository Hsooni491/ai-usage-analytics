{# Use the custom schema name as-is (gold) instead of "<target_schema>_gold". #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ (custom_schema_name or target.schema) | trim }}
{%- endmacro %}
