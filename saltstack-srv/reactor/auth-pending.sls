{% if 'act' in data and data['act'] == 'pend' and data['id'] in salt['dynamictorque.get_starting_instance_names'](pillar['get_starting_instance_names_cmd']) %}
minion_add:
  wheel.key.accept:
    - match: {{ data['id'] }}
{% endif %}