{#
  Maps the free-text, multilingual profession (EN / PT / DE / FR) to a job family.
  Order matters: the first matching rule wins.
#}
{% macro profession_category(col) -%}
    {%- set rules = [
        ("Administration & Operations", ["data entry", "admin", "assistente", "project manager", "projektmanager"]),
        ("Customer Support",            ["customer", "kunden", "atendimento", "support operations", "ai support"]),
        ("Software & IT",               ["software", "developer", "desenvolv", "développeur", "entwickl", "tech lead",
                                         "technical lead", "web ", "computer science", "information technology",
                                         "solutions architect", "systems developer", "support technician"]),
        ("Data & AI",                   ["data", "dados", "données", "datenanalyst", "analytics", "analyst", "statistic",
                                         "business intelligence", "machine learning", "artificial intelligence",
                                         "inteligência", "bioinformatics"]),
        ("Humanities",                  ["literature", "history", "creative writing", "comparative"]),
        ("Content, Media & Marketing",  ["content", "conteúdo", "contenu", "marketing", "marketer", "social media",
                                         "media", "writer", "multimedia"]),
        ("Research & Academia",         ["research", "pesquisador", "professor", "scientist"]),
        ("Engineering",                 ["engineering"]),
        ("Natural & Social Sciences",   ["biology", "biotech", "biomedical", "physics", "mathematics", "environmental",
                                         "psychology", "science"]),
        ("Business",                    ["business"]),
    ] -%}
    case
        when {{ col }} is null or {{ col }} = 'Unknown' then 'Unknown'
    {%- for category, keywords in rules %}
        when {% for kw in keywords %}lower({{ col }}) like '%{{ kw }}%'{% if not loop.last %} or {% endif %}{% endfor %}
            then '{{ category }}'
    {%- endfor %}
        else 'Other'
    end
{%- endmacro %}
