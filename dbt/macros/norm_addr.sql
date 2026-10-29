{# Uppercase, strip punctuation, collapse whitespace. Used on both sides of the
   Price Paid <-> EPC address match so "Flat 2, 10 High St." == "FLAT 2 10 HIGH ST". #}
{% macro norm_addr(expr) -%}
trim(regexp_replace(regexp_replace(upper(coalesce({{ expr }}, '')), r'[^A-Z0-9 ]', ' '), r'\s+', ' '))
{%- endmacro %}
