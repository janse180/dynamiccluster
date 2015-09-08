mom-package:
  file:
    - managed
    - name: /tmp/torque-package-mom-linux-x86_64.sh
    - source: salt://torque/torque-package-mom-linux-x86_64.sh
    - user: root
    - group: root
    - mode: 700

mom-install:
  cmd:
    - run
    - name: /tmp/torque-package-mom-linux-x86_64.sh --install
    - require:
      - file: mom-package
    - unless: test -f /usr/local/sbin/pbs_mom

mom-initd:
  file:
    - managed
    - name: /etc/init.d/pbs_mom
    - source: salt://torque/pbs_mom
    - template: jinja
    - user: root
    - group: root
    - mode: 755

mom-config:
  file:
    - managed
    - template: jinja
    - name: /var/spool/torque/mom_priv/config
    - source: salt://torque/mom_config
    - context: {
      server_name: "{{ pillar['headnode_fqdn'] }}"
      }
    - user: root
    - group: root
    - mode: 644
    - makedirs: True

servername-file:
  file:
    - managed
    - name: /var/spool/torque/server_name
    - source: salt://torque/server_name
    - template: jinja
    - context: {
      server_name: "{{ pillar['headnode_fqdn'] }}"
      }
    - user: root
    - group: root
    - mode: 644
    - makedirs: True

pbs_mom:
  service.running:
    - enable: True
    - sig: pbs_mom
    - require:
      - cmd: mom-install
      - file: mom-initd
    - watch:
      - file: mom-config
      - file: servername-file
    