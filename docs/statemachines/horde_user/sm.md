{% macro image_url(url) %}
{%- if config.site_url|length -%}
{{ config.site_url }}{{ url }}
{%- else -%}
{{ fix_url(url) }}
{%- endif -%}
{% endmacro %}

# Horde User (`ait.horde_user`)

The Horde user activity simulates a user of the group ware software [Horde](https://www.horde.org/) most notably its web mail feature.
It has various sub activities for the specific horde menus e.g.m mails, calendar, etc.


<figure>
  <a data-fancybox="gallery" href="{{ image_url("statemachines/horde_user/horde_user.svg") }}">
  <img src="{{ image_url("statemachines/horde_user/horde_user.svg") }}" alt="Horde user state machine" />
  <figcaption>Horde user state machine</figcaption>
  </a>
</figure>

## Configuration

::: cr_kyoushi.statemachines.horde_user.config
    rendering:
      show_source: false
      show_root_toc_entry: False
      heading_level: 3

## Context

::: cr_kyoushi.statemachines.horde_user.context
    rendering:
      show_source: false
      show_root_toc_entry: False
      heading_level: 3
