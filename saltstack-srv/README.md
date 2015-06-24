### Salt Master config

/etc/salt/master
```
runner_dirs: ["/srv/runner"]
```

/etc/salt/master.d/reactor.conf
```
reactor:
  - 'salt/auth':
      /srv/reactor/auth-pending.sls
  - 'salt/minion/devwn-*/start':
    - /srv/reactor/wn-start.sls
```