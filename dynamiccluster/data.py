import json
import time
import inspect
import sys

class EnumBase: # base class of all Enums
    @classmethod
    def tostring(cls, value):
        return dict((v,k) for k,v in cls.__dict__.iteritems())[value]

    @classmethod
    def fromstring(cls, name):
        return cls.__dict__[name]
    
class WorkerNode(EnumBase):
    Inexistent, Starting, Idle, Busy, Error, Deleting, Holding, Held = range(8)
    def __init__(self, hostname=None, type="Physical"):
        self.hostname=hostname
        self.type=type
        self.jobs=None
        self.state=WorkerNode.Inexistent
        self.state_start_time=0
        self.num_proc=0
        self.extra_attributes=None
        self.time_in_current_state=0
        self.instance=None
        
    def __repr__(self):
        if self.state_start_time>0:
            self.__dict__.update({'time_in_current_state':time.time()-self.state_start_time})
        return json.dumps(self, default=lambda o: o.__dict__)
        
class Instance(EnumBase):
    Inexistent, Pending, Starting, Active, Ready, Deleting, Error, Unknown = range(8)
    def __init__(self, uuid):
        self.uuid=uuid
        self.instance_name=None
        self.state=Instance.Inexistent
        self.ip=None
        self.dns_name=None
        self.vcpu_number=0
        self.flavor=None
        self.key_name=None
        self.security_groups=None
        self.availability_zone=None
        self.image_uuid=None
        self.subnet_id=None
        self.creation_time=0
        self.cloud_resource=None
        self.last_update_time=0
        self.tasked=False
        self.last_task_result=-1
        self.spot_id=None
        self.spot_state=None
        self.spot_price=0
    def __repr__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class Job(object):
    Queued, Running, Other = range(3)
    def __init__(self, jobid):
        self.jobid=jobid
        self.priority=-1
        self.name=None
        self.owner=None
        self.state=None
        self.queue=None
        self.property=None
        self.account=None
        self.requested_cores=1
        self.cores_per_node=1
        self.requested_mem=None
        self.requested_walltime=None
        self.creation_time=0
        self.extra_attributes=None
    def __repr__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class ClusterInfo(object):
    def __init__(self, workernodes=[], queued_jobs=[], total_queued_job_number=0):
        self.worker_nodes=workernodes
        self.queued_jobs=queued_jobs
        self.total_queued_job_number=total_queued_job_number
        
class CloudResource(object):
    def __init__(self, name, **kwargs):
        self.name=name
        self.priority=kwargs['priority']
        self.type=kwargs['type']
        self.min_num=kwargs['quantity']['min']
        self.max_num=kwargs['quantity']['max']
        self.current_num=0
        self.cores_per_node=0
        self.proposed_allocation=None
        self.config=kwargs['config']
        if 'queue' in kwargs['reservation']:
            self.reservation_queue=kwargs['reservation']['queue']
        else:
            self.reservation_queue=None
        if 'account' in kwargs['reservation']:
            self.reservation_account=kwargs['reservation']['account']
        else:
            self.reservation_account=None
        if 'property' in kwargs['reservation']:
            self.reservation_property=kwargs['reservation']['property']
        else:
            self.reservation_account=None
    def __repr__(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        