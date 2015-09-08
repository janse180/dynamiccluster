send_result:
  runner.graphite.send:
    - minion_id: {{ data['id'] }}
    - data: {{ data['data'] }}
    - host: localhost
    - port: 2003
