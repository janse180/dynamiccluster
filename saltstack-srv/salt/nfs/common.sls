nfs-utils:
  pkg.installed

rpcbind:
  service.running:
    - enable: True
    - require:
      - pkg: nfs-utils
