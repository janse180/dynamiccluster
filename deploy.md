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


Note: pip 7.1 seems not compatible with novaclient. But pip 1.3.0 works fine though. python-pip in EPEL is 7.1, if you want to use pip 1.3.0, you need to use easy_install to get it.


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

Create your config file /etc/dynamiccluster/dynamiccluster.yaml. An example is /opt/dynamiccluster/config/dynamiccluster.yaml

For details on how to change this configuration file, please see [Configuration](#configuration) below.

If you want to put log files in /var/log/dynamiccluster, please create that directory.

## Install RPM package

RPMs can be found in [CITC](https://github.com/eResearchSA/citc/tree/master/rpms). We don't have a yum repo so we only publish RPM files.

Use yum to install it and yum will sort out the dependencies, e.g.


	yum localinstall -y https://github.com/eResearchSA/citc/raw/master/rpms/dynamiccluster-1.0.0-1.el6.noarch.rpm


# Configuration

The configuration file include four sections. An example can be found [here](https://github.com/eResearchSA/citc/blob/master/all-in-one/srv/salt/dynamiccluster/dynamiccluster.yaml).

## General dynamic cluster variables

This section includes variables for dynamic cluster itself. All time interval variables are optional. If they don't appear in the config file, the default value will be used.

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
    
Auto provision interval (in seconds) is the time interval that Dynamic Cluster checks queueing jobs to see if new worker nodes are needed. The default value is 60.
    
    auto_provision_interval: 60
    
Number of workers. Dynamic Cluster spawns multiple processes to communicate with cloud systems.
    
    worker_number: 2
    
Automatic mode. Dynamic cluster works out for you which worker node to kill and how many to fire up according to work load. Setting it to False will turn it into a static cluster, but the admin can still add or remove worker nodes manually.
    
    auto_mode: True
    
The port number of the built-in admin server, which serves the Restful API and a web-based dashboard.

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
        
A script can be executed after cloud provisioning is finished (VM state in the cloud becomes ACTIVE in OpenStack or Running in AWS) 
It takes three parameters which are the hostname of the VM, the IP of the VM and its name in dynamic torque.
This is optional.
    
    post_vm_provision_command: /the/path/some.sh {0} {1} {2}
    
A script can be executed after a VM is destroyed from the cloud.
It takes three parameters which are the hostname of the VM, the IP of the VM and its name in dynamic torque.
This is optional.

    post_vm_destroy_command: /the/path/some.sh {0} {1} {2}


## Cluster specific variables

Dynamic cluster supports Torque and SGE. _type_ defines which cluster to use.

    cluster:
      type: torque
      config:
        ...

Or

    cluster:
      type: sge
      config:
        ...

Several variables in config are common:

A list of queues that dynamic cluster cares about.

    queue_to_monitor: 
      - short
      - long

The number of queued jobs to keep in memory for display. Because a queue can have thousands of pending jobs, we only display a certain number.

    queued_job_number_to_display: 30

A script can be executed after adding a node to the cluster.
It takes two parameters which are the hostname of the VM and the IP of the VM.
This is optional.

    post_add_node_command: /the/path/some.sh {0} {1}
    
A script can be executed after removing a node from the cluster.
It takes two parameters which are the hostname of the VM and the IP of the VM.
This is optional.

    post_remove_node_command: /the/path/some.sh {0} {1}

Variables related to cluster commands are cluster specific. They can stay as it is because they are used by the code. The admin just needs adjust the path accordingly.

### Torque variables

The command to query jobs in the queue. it must return data in XML format (-x).

    qstat_command: /usr/bin/qstat -x -t
    
The command to run pbsnodes command with different options. It must return data in XML format (-x).
It takes two parameters, the option and the hostname of the VM:

* -x query node's details
* -o hold node (set it to offline)
* -c release node (clear OFFLINE)
    
<pre><code>pbsnodes_command: /usr/bin/pbsnodes {0} {1}</code></pre>
    
The command to add a new node to torque. It takes one parameter which is the hostname of the VM.

    add_node_command: /usr/bin/qmgr -c "create node {0}"
    
The command to check node state in maui. It takes one parameter which is the hostname of the VM.

    check_node_command: /usr/bin/checknode {0}
    
The command to delete node from torque. It takes one parameter which is the hostname of the VM.

    remove_node_command: /usr/bin/qmgr -c "delete node {0}"
    
The command to set a property to node in torque. It takes three parameters: {0} is the hostname of the VM, {1} is the name of the property, {2} is the value of the property.

    set_node_command: /usr/bin/qmgr -c "set node {0} {1} {2} {3}"
    
The command to get jobs' priorities.

    diagnose_p_command: /usr/bin/diagnose -p
    
The command to show reservations of a node.

    showres_command: /usr/bin/showres -n | grep {0}

The command to set account_string to a node.

    setres_command: /usr/bin/setres {0} {1} {2}
    
The command to unset account_string in a node.

    releaseres_command: /usr/bin/releaseres `/usr/bin/showres -n | grep User | grep {0} | grep {1} | awk '{{print $3}}' `

The command to delete a job.

    delete_job_command: /usr/bin/qdel -p {0}

The command to send a signal to a job.

    signal_job_command: /usr/bin/qsig -s {0} {1}
      

### SGE variables

The command to query jobs in the queue. It must return data in XML format (-xml)

    qstat_command: /opt/sge/bin/lx-amd64/qstat -xml -r
    
The command to run qhost command with differnt options. The two parameters are "-h hostname", if present it will query only one host.

    qhost_command: /opt/sge/bin/lx-amd64/qhost -q -j -xml {0} {1}
    
The command to modify hostgroup in sge, used when adding or removing a node.
It takes three parameters which are -aattr/-dattr, the hostname of the VM and the group name

    hostgroup_command: /opt/sge/bin/lx-amd64/qconf {0} hostgroup hostlist {1} {2}
    
The command to enable/disable all queue in a node. 
It takes two parameters which are -e(enable)/-d(disable) and the hostname of the VM

    qmod_command: /opt/sge/bin/lx-amd64/qmod {0} *@{1}
    
The command to delete node from torque.
It takes one parameter which is the hostname of the VM

    remove_node_command: /opt/sge/bin/lx-amd64/qconf -de {0}
    
The command to set slots in a queue for a node.
It takes one parameter which are the number of slots, queue name and the hostname of the VM

    set_slots_command: /opt/sge/bin/lx-amd64/qconf -rattr queue slots {0} {1}@{2}
    
The command to unset slots in a queue for a node before removing this node.
It takes one parameter which are queue name and the hostname of the VM

    unset_slots_command: /opt/sge/bin/lx-amd64/qconf -purge queue slots {0}@{1}
    
The command to run qconf -spl command

    qconf_spl_command: /opt/sge/bin/lx-amd64/qconf -spl

The command to run qconf -sp command to get allocation rule

    qconf_sp_command: /opt/sge/bin/lx-amd64/qconf -sp {0} | grep allocation_rule | awk '{{print $2}}'

The command to run qdel -f command to force deletion of a dead job

    qdel_command: /opt/sge/bin/lx-amd64/qdel -f {0}
    
## Cloud variables

The cloud section specifies cloud resources. Each resource can be an openstack resource or an AWS resource, which is set in _type_. They have some variables in common.

Reservation speficies the limitation when a resource is added. The limitation can restrict the resource to a queue, an account string, or a property.

For Torque:

* queue reservation is achieved by using maui's "setres -q" command, which reserves the worker node for a particular queue.
* account reservation is achieved by using maui's "setres -a" command, which reserves the worker node for an account string. To use this worker node, the user needs to add "-A" to qsub command.
* property reservation is achieved by setting a property to the worker node in Torque.

For SGE:

* queue reservation is achieved by adding the node to slots of a queue.
* account reservation is achieved by adding the node to a hostgroup.
* property reservation is not used.

When a job is submitted to the queue, Dynamic Cluster matches job requirements with resource reservation to find a suitable resource. Then a worker node will be launched using this resource.

Quantity defines the minimum number and maximum number of worker nodes in this resource.

Priority sets the priority of the resource, lower number means higher priority. If multiple resources are suitable for a job, the highest priority one will be chosen. If they have the same priority, the one with less worker nodes will be chosen.


    resource-name:
      type: openstack/aws
      reservation:
        queue:
        account:
        property:
      quantity:
        min:
        max:
      priority:
      config:
        ...
        

### OpenStack specific variables

Dynamic cluster uses Nova API to talk to OpenStack.

Username of user's openstack account
  
      username:

Password of user's openstack account

      password:

Project (or tenant) of user's openstack account

      project:

Image UUID

      image_uuid:

Flavor of worker node, e.g. m1.small

      flavor:

OpenStack's auth URL (Keystone URL)

      auth_url:

SSH key name

      key_name:

Security groups, in list

      security_groups:

Avaiablility zone, if multi-zones are available, each zone is one resource.

      availability_zone:

Prefix of instance name, this is used to get all instances for the resource. Please use a different name for each resource.

      instance_name_prefix:

User-data script file

      userdata_file:
      
### AWS specific variables
 
Dynamic Cluster uses boto to talk to AWS.

Access key ID of user's AWS account

      access_key_id:

Secret access key of user's AWS account

      secret_access_key:

Image ID

      image_id:

Instance type

      instance_type:

Region name

      region_name: 

SSH key name

      key_name:

Security groups, must use ID if subnet_id is used

      security_groups:

Availability zone

      availability_zone:

Subnet ID

      subnet_id:

Boolean variable, specifies whether assigns a public IP to the instance

      use_public_ip_address:

Prefix of instance name

      instance_name_prefix:

User-data script file

      userdata_file:

Spot price

      spot_bid:

Timeout of Spot price

      spot_timeout:

HTTP proxy hostname (optional)

      proxy:

HTTP proxy port (optional)

      proxy_port:
      
## Plugin section

Dynamic cluster supports plugins. A plugin runs as a thread in the main process.

Currently there is only one plugin.

The graphite plugin sends the number of worker nodes and cores to graphite every minute.

    graphite:
      class_name: dynamiccluster.graphite.GraphiteReporter
      arguments:
        hostname: localhost
        port: 2003
        prefix: headnode.dynamiccluster

## Logging section

Dynamic cluster uses python's built-in logging module for logs.

Log level.

* 0 ERROR
* 1 WARNING
* 2 INFO
* 3 DEBUG

<pre><code>log_level: 3</code></pre>
    
Path of log file.
    
    log_location: /tmp/dynamiccluster.log
    
Log format.
    
    log_format: "%(asctime)s - %(levelname)s - %(processName)s - %(threadName)s - %(message)s"
    
Maximum size of log file, it will rotate if exceeds and keep recent 3 rotated logs.
    
    log_max_size: 2097152

