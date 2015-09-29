---
layout: home
title: Dynamic Cluster - Deployment
slug: deploy
permalink: /deploy.html
---

# Cloud library installation

Depending on the cloud you use, its client library needs to be installed.

## OpenStack


	yum install -y python-pip gcc-c++ python-devel git


and then


	pip install python-novaclient


Note: pip 7.1 seems not compatible with novaclient. But pip 1.3 works fine though. python-pip in epel is 7.1, if you want to use pip 1.3, you need to use easy_install to get it.


	easy_install pip==1.3.0



## AWS


	yum install -y python-pip gcc-c++ python-devel git


and then


	pip install boto

# Installation

You can install dynamic cluster from source code or using a RPM.

## Install from Source

You can clone its git repo or download the source tar ball from github. The document assumes the source is in /opt/dynamiccluster.

Install its dependencies.


	pip install -r /opt/dynamiccluster/reqirements.txt


Copy init.d script from /opt/dynamiccluster/scripts/ to /etc/init.d


	cp /opt/dynamiccluster/scripts/initd-script /etc/init.d/dynamiccluster

Create your config file. An example is in /opt/dynamiccluster/config/dynamiccluster.yaml

For details on how to change this configuration file, please see [Configuration](#configuration) below.

If you want to put log files in /var/log/dynamiccluster, please create that directory.

## Install RPM package

RPMs can be found in [CITC](https://github.com/eResearchSA/citc/tree/master/rpms). We don't have a yum repo so we only publish RPM files.

Use yum to install it and yum will sort out the dependencies, e.g.


	yum localinstall -y https://github.com/eResearchSA/citc/raw/master/rpms/dynamiccluster-0.5.0-1.el6.noarch.rpm


# Configuration

The configuration file include four sections.

## General dynamic cluster parameters


Max idle time (in seconds) is the amount of time a worker node can be idle for before it will be deleted. The default value is 600.
    
    max_idle_time: 600
    
Max down time (in seconds) is the amount of time a worker node can be down (in error state) for before it will be deleted. The default value is 480.
default is 480

    max_down_time: 480
    
Max launch time (in seconds) is the maximum amount of time it takes for an instance to be built in the cloud, from when a request is sent to the cloud.
If the instance is still not in a useful state after this time, it will be destroyed. The default value is 1200.
    
    max_launch_time: 1200
    
Cluster poller interval (in seconds) is the time interval that Dynamic Cluster queries the cluster. The default value is 10.
    
    cluster_poller_interval: 10
    
Cloud poller interval (in seconds) is the time interval that Dynamic Cluster queries the cloud. The default value is 20.
    
    cloud_poller_interval: 20
    
Auto provision interval (in secondes) is the time interval that Dynamic Cluster checks queueing jobs to see if new worker nodes are needed. The default value is 60.
    
    auto_provision_interval: 60
    
number of workers
    
    worker_number: 2
    
auto mode, dynamic cluster works out which one to kill and how many to fire up according to work load
    
    auto_mode: True
    
The port number of the built-in admin server, which serves a Restful API and a web-based dashboard.

    admin-server:
      port: 8001
      
The method to check if a new instance has finished configuration. Two methods are built-in. Users can write their custom checkers.
Port checker checks a port to see if it is listening.

    config-checker:
      port:
        number: 15002

Salt checker uses salt client to check an instance's highstate.
        
    config-checker:
      plugin:
        name: dynamiccluster.salt.SaltChecker
        
a script to be executed after cloud provisioning is finished (VM state in the cloud becomes ACTIVE) 
it takes two parameters which are the hostname of the VM, the IP of the VM and its name in dynamic torque
    
    #post_vm_provision_command: /the/path/some.sh {0} {1} {2}
    
a script to be executed after a VM is destroyed from the cloud
it takes two parameters which are the hostname of the VM, the IP of the VM and its name in dynamic torque

    #post_vm_destroy_command: /the/path/some.sh {0} {1} {2}


## cluster

  type: torque
  config:
    queue_to_monitor: 
      - short
      - long
    # the number of queued jobs to keep in memory for display
    queued_job_number_to_display: 30
    # the command to query jobs in the queue
    #  it must return data in XML format (-x)
    qstat_command: /usr/bin/qstat -x -t
    
    # the command to run pbsnodes command with differnt options
    #  it takes two parameters, the option and the hostname of the VM
    #    -x query node's details
    #    -o hold node (set it to offline)
    #    -c release node (clear OFFLINE)
    #  it must return data in XML format (-x)
    pbsnodes_command: /usr/bin/pbsnodes {0} {1}
    
    # the command to add a new node to torque
    #  it takes one parameter which is the hostname of the VM
    add_node_command: /usr/bin/qmgr -c "create node {0}"
    
    # the command to check node state in maui
    #  it takes one parameter which is the hostname of the VM
    check_node_command: /usr/bin/checknode {0}
    
    # the command to delete node from torque
    #  it takes one parameter which is the hostname of the VM
    remove_node_command: /usr/bin/qmgr -c "delete node {0}"
    
    # the command to set a property to node in torque
    #  it takes three parameters {0} is the hostname of the VM, {1} is the name of the property, {2} is the value of the property
    set_node_command: /usr/bin/qmgr -c "set node {0} {1} {2} {3}"
    
    # the command to get jobs' priorities
    diagnose_p_command: /usr/bin/diagnose -p
    
    # the command to show reservations of a node
    showres_command: /usr/bin/showres -n | grep {0}

    # the command to set account_string to a node
    setres_command: /usr/bin/setres {0} {1} {2}
    
    # the command to unset account_string in a node
    releaseres_command: /usr/bin/releaseres `/usr/bin/showres -n | grep User | grep {0} | grep {1} | awk '{{print $3}}' `

    # the command to delete a job
    delete_job_command: /usr/bin/qdel -p {0}

    # the command to send a signal to a job
    signal_job_command: /usr/bin/qsig -s {0} {1}
      
    # a script to be executed after adding a node to Torque (just before setting it to online) 
    #  it takes two parameters which are the hostname of the VM and the IP of the VM
    #post_add_node_command: /the/path/some.sh {0} {1}
    
    # a script to be executed after removing a node from Torque (after it is destroyed from the cloud)
    #  it takes two parameters which are the hostname of the VM and the IP of the VM
    #post_remove_node_command: /the/path/some.sh {0} {1}

## cluster

  type: sge
  config:
    queue_to_monitor: 
      - short
      - long
    # the number of queued jobs to keep in memory for display
    queued_job_number_to_display: 30
    # the command to query jobs in the queue
    #  it must return data in XML format (-xml)
    qstat_command: /opt/sge/bin/lx-amd64/qstat -xml -r
    
    # the command to run qhost command with differnt options
    #  it takes two parameters to query only one host, "-h hostname"
    qhost_command: /opt/sge/bin/lx-amd64/qhost -q -j -xml {0} {1}
    
    # the command to modify hostgroup in sge, used when adding or removing a node
    #  it takes three parameters which are -aattr/-dattr, the hostname of the VM and the group name
    hostgroup_command: /opt/sge/bin/lx-amd64/qconf {0} hostgroup hostlist {1} {2}
    
    # the command to enable/disable all queue in a node
    #  it takes two parameters which are -e(enable)/-d(disable) and the hostname of the VM
    qmod_command: /opt/sge/bin/lx-amd64/qmod {0} *@{1}
    
    # the command to delete node from torque
    #  it takes one parameter which is the hostname of the VM
    remove_node_command: /opt/sge/bin/lx-amd64/qconf -de {0}
    
    # the command to set slots in a queue for a node
    #  it takes one parameter which are the number of slots, queue name and the hostname of the VM
    set_slots_command: /opt/sge/bin/lx-amd64/qconf -rattr queue slots {0} {1}@{2}
    
    # the command to unset slots in a queue for a node before removing this node
    #  it takes one parameter which are queue name and the hostname of the VM
    unset_slots_command: /opt/sge/bin/lx-amd64/qconf -purge queue slots {0}@{1}
    
    # the command to run qconf -spl command
    qconf_spl_command: /opt/sge/bin/lx-amd64/qconf -spl

    # the command to run qconf -sp command to get allocation rule
    qconf_sp_command: /opt/sge/bin/lx-amd64/qconf -sp {0} | grep allocation_rule | awk '{{print $2}}'

    # the command to run qdel -f command to force deletion of a dead job
    qdel_command: /opt/sge/bin/lx-amd64/qdel -f {0}
    
## cloud

  os-res:
    type: openstack
    reservation:
      queue:
      account:
      property:
    quantity:
      min:
      max:
    priority:
    config:
      username:
      password:
      project:
      image_uuid:
      flavor:
      auth_url:
      key_name:
      security_groups:
      availability_zone:
      instance_name_prefix:
      userdata_file:
  aws-res:
    type: aws
    reservation:
      queue:
      account:
      property:
    quantity:
      min:
      max:
    priority:
    config:
      access_key_id:
      secret_access_key:
      image_id:
      instance_type:
      region_name: ap-southeast-2
      key_name:
      security_groups:
      availability_zone:
      subnet_id:
      use_public_ip_address:
      instance_name_prefix:
      userdata_file:
      validate_certs: False
      spot_bid:
      spot_timeout:
      #proxy:
      #proxy_port:
      
## plugins

  graphite:
    class_name: dynamiccluster.graphite.GraphiteReporter
    arguments:
      hostname: localhost
      port: 2003
      prefix: headnode.dynamiccluster

## logging

    log_level: 3
    log_location: /tmp/dynamiccluster.log
    log_format: "%(asctime)s - %(levelname)s - %(processName)s - %(threadName)s - %(message)s"
    log_max_size: 2097152

