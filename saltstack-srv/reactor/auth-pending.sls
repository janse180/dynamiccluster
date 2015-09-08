{% if 'act' in data and data['act'] == 'pend' %}
minion_add:
  runner.dynamiccluster.process_minion_request:
    - minion_id: {{ data['id'] }}
{% endif %}