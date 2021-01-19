{% macro image_url(url) %}
{%- if config.site_url|length -%}
{{ config.site_url }}{{ url }}
{%- else -%}
{{ fix_url(url) }}
{%- endif -%}
{% endmacro %}

The Web Browser state machine simulates a person browsing the internet. It connects
to random websites and browses links on it using Selenium.

<figure>
  <a data-fancybox="gallery" href="{{ image_url("statemachines/web_browser.svg") }}">
  <img src="{{ image_url("statemachines/web_browser.svg") }}" alt="Web Browser state machine" />
  <figcaption>Web Browser state machine</figcaption>
  </a>
</figure>

## Configuration

::: cr_kyoushi.statemachines.web_browser.config:StatemachineConfig
    rendering:
      show_source: false
      show_root_heading: true
      heading_level: 3

::: cr_kyoushi.statemachines.web_browser.config:UserConfig
    rendering:
      show_source: false
      show_root_heading: true
      heading_level: 3

::: cr_kyoushi.statemachines.web_browser.config:StatesConfig
    rendering:
      show_source: false
      show_root_heading: true
      heading_level: 3

::: cr_kyoushi.statemachines.web_browser.config:ActivitySelectionStateConfig
    rendering:
      show_source: false
      show_root_heading: true
      heading_level: 4

::: cr_kyoushi.statemachines.web_browser.config:WebsiteStateConfig
    rendering:
      show_source: false
      show_root_heading: true
      heading_level: 4

::: cr_kyoushi.statemachines.web_browser.config:LeaveWebsiteStateConfig
    rendering:
      show_source: false
      show_root_heading: true
      heading_level: 4
