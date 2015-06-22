ntp:
  pkg:
    - installed
  service:
    - name: ntpd
    - running
    - enable: True
    - require:
      - pkg: ntp
    - watch:
      - file: ntp.conf

ntp.conf:
  file.managed:
    - name: /etc/ntp.conf
    - source: salt://ntp/ntp.conf
    - template: jinja
    - user: root
    - group: root
    - mode: 644