#!/bin/bash

yum install -y salt-minion
# salt config
#mkdir /etc/salt
#cat << EOF > /etc/salt/minion
#master: {{ grains['fqdn'] }}
#EOF
#cat << EOF > /etc/salt/minion_id
##{{ '{{' }} minion_id {{ '}}' }}
#EOF
#chkconfig salt-minion on