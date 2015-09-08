home:
  mount.mounted:
    - name: /home/users
    - device: {{ pillar['nfs_fqdn'] }}:/home
    - fstype: nfs4
    - opts: rsize=32768,wsize=32768,noatime,nodiratime,soft,_netdev
    - persist: True
    - mkmnt: True

sw:
  mount.mounted:
    - name: /sw
    - device: {{ pillar['nfs_fqdn'] }}:/sw
    - fstype: nfs4
    - opts: rsize=32768,wsize=32768,noatime,nodiratime,soft,_netdev
    - persist: True
    - mkmnt: True
    
data:
  mount.mounted:
    - name: /data
    - device: {{ pillar['nfs_fqdn'] }}:/home
    - fstype: nfs4
    - opts: rsize=32768,wsize=32768,noatime,nodiratime,soft,_netdev
    - persist: True
    - mkmnt: True
    