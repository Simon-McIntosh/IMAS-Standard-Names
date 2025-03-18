# Standard names

{% for name, attrs in standardnames.items() %}

## `{{name}}`

{% if attrs["units"] == "" %}

- _units_: dimensionless

{% else %}

- _units_: {{attrs["units"]}}

{% endif %}

{% if "tags" in attrs %}

- _tags: {{ ", ".join(attrs["tags"]) }}_

{% endif %}

{{ attrs["documentation"] }}
{% endfor %}
