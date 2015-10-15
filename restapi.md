---
layout: home
title: Dynamic Cluster - Restful API
slug: restapi
permalink: /restapi.html
---

## Restful API

The Restful API is the main approach to manipulate Dynamic Cluster. It doesn't have any authentication so you can place it behind Apache or Nginx to protect it. An example can be found [here](https://github.com/eResearchSA/citc/blob/master/all-in-one/srv/salt/httpd/ssl.conf).

All responses are in JSON format.

### GET /workernode

Returns a list of worker nodes.

#### Parameters

* state (optional) only return worker nodes in this state
  * 0 Inexistent
  * 1 Starting
  * 2 Idle
  * 3 Busy
  * 4 Error
  * 5 Deleting
  * 6 Holding
  * 7 Held
  
#### example response

<pre lang="javascript"><code>[
  {
    "extra_attributes": {
      "status": "rectime=1443596649, varattr=, jobs=,state=free, netload=2900659113, gres=, loadave=0.00, ncpus=1, physmem=3925324kb, availmem=5136716kb, totmem=5498180kb, idletime=607366, nusers=0, nsessions=0, uname=Linux cw-vm-d05e.sa.nectar.org.au 2.6.32-279.el6.x86_64 #1 SMP Fri Jun 22 12:19:21 UTC 2012 x86_64,opsys=linux", 
      "mom_manager_port": "15003", 
      "ntype": "cluster", 
      "mom_service_port": "15002"
    }, 
    "num_proc": 1, 
    "jobs": null, 
    "hostname": "cw-vm-d05e.sa.nectar.org.au", 
    "time_in_current_state": 606848, 
    "state_start_time": 0, 
    "instance": {
      "last_update_time": 0, 
      "last_task_result": -1, 
      "spot_price": 0, 
      "uuid": "7a0b2efe-0eda-42f4-9ad3-ac779be1b2cf", 
      "availability_zone": "sa", 
      "subnet_id": null, 
      "ip": "130.220.208.94", 
      "spot_id": null, 
      "creation_time": 1442989256.0, 
      "tasked": false, 
      "vcpu_number": 1, 
      "instance_name": "dynamicwn-Mmp2O3y1", 
      "cloud_resource": "os-res", 
      "state": 4, 
      "spot_state": null, 
      "security_groups": ["dc-dynamic_cluster_wn-vgg7h5udejdb"], 
      "dns_name": "cw-vm-d05e.sa.nectar.org.au", 
      "image_uuid": "1b66d8cd-7d10-413a-ae06-3b61560e788a", 
      "flavor": "m1.small", 
      "key_name": "ersakey"
    }, 
    "state": 2, 
    "type": "openstack"
  }
]
</code></pre>

### GET /workernode/\<hostname\>

Returns a worker node specified by hostname. Its response is one item in the above list.

#### Error code

* 404 if the hostname is not found.

### PUT /workernode/\<hostname\>/\<action\>

Manipulate a worker node specified by hostname. Action can be one of *hold*, *unhold* and *vacate*.

* hold: disable the worker node. If it has running jobs they will continue to run, but the worker node will not accept new jobs.
* unhold: enable the worker node. Set it back to normal.
* vacate: force deletion of all running jobs. You may want to hold it first otherwise new jobs will be scheduled on it once existing jobs are deleted.

#### Example response

    {
      "success": True
    }

#### Error code

* 404 if the hostname is not found or the action is not supported.
* 400 if the action is not allowed in the current state.
* 500 for other errors.

### DELETE /workernode/\<hostname\>

Delete a worker node specified by hostname.

#### Example response

    {
      "success": True
    }

#### Error code

* 404 if the hostname is not found.
* 400 if the action is not allowed in the current state. A worker node can only be deleted when it is in *Held* state and has no running jobs, or in *Starting* or *Error*.
* 500 for other errors.

### GET /job

Returns a list of queued jobs.

#### example response

<pre lang="javascript"><code>[
  {
    "queue": "default", 
    "account": null, 
    "name": "longjob", 
    "requested_mem": null, 
    "cores_per_node": 1, 
    "creation_time": "1443597955", 
    "requested_cores": 1, 
    "requested_walltime": "00:50:00", 
    "jobid": "13", 
    "priority": 0, 
    "state": 0, 
    "owner": "fred@cw-vm-d026.sa.nectar.org.au", 
    "extra_attributes": {
      "Variable_List": "PBS_O_QUEUE=default,PBS_O_HOME=/home/fred,PBS_O_LOGNAME=fred,PBS_O_PATH=/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/home/fred/bin,PBS_O_MAIL=/var/spool/mail/fred,PBS_O_SHELL=/bin/bash,PBS_O_LANG=en_US.UTF-8,PBS_O_WORKDIR=/data,PBS_O_HOST=cw-vm-d026.sa.nectar.org.au,PBS_O_SERVER=cw-vm-d026.sa.nectar.org.au", 
      "submit_host": "cw-vm-d026.sa.nectar.org.au", 
      "submit_args": "test.sub"
    }, 
    property": null
  }
]</code></pre>

### GET /job/\<id\>

Returns a job specified by id. Its response is one item in the above list.

#### Error code

* 404 if the id is not found.

### GET /server/config

Returns server config. This is the json version of the YAML config file.

#### example response

	{
	    "cloud": {
	        "os-res": {
	            "config": {
	                "auth_url": "https://keystone.rc.nectar.org.au:5000/v2.0/",
	                "availability_zone": "sa",
	                "flavor": "m1.small",
	                "flavor_id": "0",
	                "image_uuid": "1b66d8cd-7d10-413a-ae06-3b61560e788a",
	                "instance_name_prefix": "dynamicwn",
	                "key_name": "ersakey",
	                "project": "blah",
	                "security_groups": [
	                    "dc-dynamic_cluster_wn-vgg7h5udejdb"
	                ],
	                "userdata_file": "/etc/dynamiccluster/userdata_salt.sh",
	                "username": "blah"
	            },
	            "priority": 1,
	            "quantity": {
	                "max": 3,
	                "min": 1
	            },
	            "reservation": {
	                "account": null,
	                "property": null,
	                "queue": null
	            },
	            "type": "openstack"
	        }
	    },
	    "cluster": {
	        "config": {
	            "add_node_command": "/usr/bin/qmgr -c \"create node {0}\"",
	            "check_node_command": "/usr/bin/checknode {0}",
	            "delete_job_command": "/usr/bin/qdel -p {0}",
	            "diagnose_p_command": "/usr/bin/diagnose -p",
	            "pbsnodes_command": "/usr/bin/pbsnodes {0} {1}",
	            "qstat_command": "/usr/bin/qstat -x -t",
	            "queue_to_monitor": [
	                "default"
	            ],
	            "queued_job_number_to_display": 30,
	            "releaseres_command": "/usr/bin/releaseres `/usr/bin/showres -n | grep User | grep {0} | grep {1} | awk '{{print $3}}' `",
	            "remove_node_command": "/usr/bin/qmgr -c \"delete node {0}\"",
	            "set_node_command": "/usr/bin/qmgr -c \"set node {0} {1} {2} {3}\"",
	            "setres_command": "/usr/bin/setres {0} {1} {2}",
	            "showres_command": "/usr/bin/showres -n | grep {0}",
	            "signal_job_command": "/usr/bin/qsig -s {0} {1}"
	        },
	        "type": "torque"
	    },
	    "dynamic-cluster": {
	        "admin-server": {
	            "port": 8001
	        },
	        "auto_mode": true,
	        "cloud_poller_interval": 20,
	        "cluster_poller_interval": 10,
	        "config-checker": {
	            "plugin": {
	                "name": "dynamiccluster.saltclient.SaltChecker"
	            }
	        },
	        "max_down_time": 480,
	        "max_idle_time": 600,
	        "max_launch_time": 1200,
	        "post_vm_destroy_command": "/etc/dynamiccluster/wn.sh -d {0} {1} {2}",
	        "post_vm_provision_command": "/etc/dynamiccluster/wn.sh -a {0} {1} {2}",
	        "worker_number": 2
	    },
	    "logging": {
	        "log_format": "%(asctime)s - %(levelname)s - %(processName)s - %(threadName)s - %(message)s",
	        "log_level": 3,
	        "log_location": "/var/log/dynamiccluster/dynamiccluster.log",
	        "log_max_size": 2097152
	    },
	    "plugins": {
	        "graphite": {
	            "arguments": {
	                "hostname": "localhost",
	                "port": 2003,
	                "prefix": "headnode.dynamiccluster"
	            },
	            "class_name": "dynamiccluster.graphite.GraphiteReporter"
	        }
	    }
	}

### GET /server/status

Returns server status.

#### example response

    {
      "auto_mode": true, 
      "cluster": {
        "maui": true, 
        "torque": true
      }
    }
    
### PUT /server/auto

Set auto mode to True.

#### Example response

    {
      "success": True
    }

### DELETE /server/auto

Set auto mode to False.

#### Example response

    {
      "success": True
    }
    
### GET /resource

Returns a list of resources.

#### Example response

    [
      {
        "name": "os-res", 
        "proposed_allocation": null, 
        "type": "openstack", 
        "worker_nodes": [
          {
            "extra_attributes": {
              "status": "rectime=1443598314,varattr=,jobs=13.cw-vm-d026.sa.nectar.org.au,state=free,netload=2911502444,gres=,loadave=0.05,ncpus=1,physmem=3925324kb,availmem=5099960kb,totmem=5498180kb,idletime=609031,nusers=0,nsessions=0,uname=Linux cw-vm-d05e.sa.nectar.org.au 2.6.32-279.el6.x86_64 #1 SMP Fri Jun 22 12:19:21 UTC 2012 x86_64,opsys=linux", 
              "mom_manager_port": "15003", 
              "ntype": "cluster", 
              "mom_service_port": "15002"
            }, 
            "num_proc": 1, 
            "jobs": "0/13", 
            "hostname": "cw-vm-d05e.sa.nectar.org.au", 
            "time_in_current_state": 44, 
            "state_start_time": 0, 
            "instance": {
              "last_update_time": 0, 
              "last_task_result": -1, 
              "spot_price": 0, 
              "uuid": "7a0b2efe-0eda-42f4-9ad3-ac779be1b2cf", 
              "availability_zone": "sa", 
              "subnet_id": null, 
              "ip": "130.220.208.94", 
              "spot_id": null, 
              "creation_time": 1442989256.0, 
              "tasked": false, 
              "vcpu_number": 1, 
              "instance_name": "dynamicwn-Mmp2O3y1", 
              "cloud_resource": "os-res", 
              "state": 4, 
              "spot_state": null, 
              "security_groups": [
                "dc-dynamic_cluster_wn-vgg7h5udejdb"
              ], 
              "dns_name": "cw-vm-d05e.sa.nectar.org.au", 
              "image_uuid": "1b66d8cd-7d10-413a-ae06-3b61560e788a", 
              "flavor": "m1.small", 
              "key_name": "ersakey"
            }, 
            "state": 3, 
            "type": "openstack"
          }, 
          {
            "extra_attributes": null, 
            "num_proc": 1, 
            "jobs": null, 
            "hostname": "cw-vm-d0eb.sa.nectar.org.au", 
            "time_in_current_state": 133.32521605491638, 
            "state_start_time": 1443597965.3948829, 
            "instance": {
              "last_update_time": 1443598313.5520201, 
              "last_task_result": 0, 
              "spot_price": 0, 
              "uuid": "cb689e42-915f-4c98-8491-c7c26db117f3", 
              "availability_zone": "sa", 
              "subnet_id": null, 
              "dns_name": "cw-vm-d0eb.sa.nectar.org.au", 
              "creation_time": 1443597964.0, 
              "tasked": false, 
              "vcpu_number": 1, 
              "instance_name": "dynamicwn-9AJPBEdx", 
              "cloud_resource": "os-res", 
              "state": 3, 
              "spot_state": null, 
              "spot_id": null, 
              "image_uuid": "1b66d8cd-7d10-413a-ae06-3b61560e788a", 
              "flavor": "m1.small", 
              "ip": "130.220.208.235", 
              "security_groups": ["dc-dynamic_cluster_wn-vgg7h5udejdb"], 
              "key_name": "ersakey"
            }, 
            "state": 1, 
            "type": "openstack"
          }
        ], 
        "reservation_property": null, 
        "priority": 1, 
        "flag": 0, 
        "reservation_account": null, 
        "cores_per_node": 1, 
        "current_num": 2, 
        "min_num": 1, 
        "config": {
          "username": "blah", 
          "availability_zone": "sa", 
          "instance_name_prefix": "dynamicwn", 
          "key_name": "ersakey", 
          "project": "blah", 
          "userdata_file": "/etc/dynamiccluster/userdata_salt.sh", 
          "auth_url": "https://keystone.rc.nectar.org.au:5000/v2.0/", 
          "flavor_id": "0", 
          "image_uuid": "1b66d8cd-7d10-413a-ae06-3b61560e788a", 
          "flavor": "m1.small", 
          "security_groups": ["dc-dynamic_cluster_wn-vgg7h5udejdb"]
        }, 
        "max_num": 3, 
        "reservation_queue": null
      }
    ]
    
### GET /resource/\<res_name\>

Returns a resource specified by resource name. Its response is one element in the above list.

#### Error code

* 404 if the resource name is not found.

### PUT /resource/\<res\>

Launch worker nodes for the resource.

#### Parameters

* num (optional) is the number of worker nodes to launch. If omitted one worker node will be launched.

#### Example response

    {
      "success": True
    }

#### Error code

* 404 if the resource name is not found.
* 400 if request number has exceeded the limit of the resource.
* 500 for other errors.

### PUT /resource/\<res\>/\<action\>

Manipulate a resource specified by resource name. Action can be one of *freeze*, *restore* and *drain*.

* freeze: freeze the resource, so that it can't start new worker nodes or delete existing worker nodes. The trick is to set min and max number to the current number.
* restore: unfreeze the resource. Put it back to normal.
* drain: delete all worker nodes in this resource, useful when the resource is having an outage. The trick is to set min and max number to 0. You may need to vacate worker nodes if they have running jobs and you don't want to wait. Otherwise the jobs will continue to run until they finish.

#### Example response

    {
      "success": True
    }

#### Error code

* 404 if the resource name is not found or the action is not supported.
