import json

class WorkerNode(object):
    Inexistent, Starting, Idle, Busy, Error, Deleting = range(6)
    def __init__(self, hostname, type="Physical"):
        self.hostname=hostname
        self.type=type
        self.jobs=None
        self.state=WorkerNode.Inexistent
        self.state_start_time=0
        self.num_proc=0
        self.extra_attributes=None
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
        self.account_string=None
        self.requested_proc=None
        self.requested_mem=None
        self.requested_walltime=None
        self.creation_time=0
        self.extra_attributes=None
    def __repr__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class ProcRequirement(object):
    def __init__(self, num_nodes=1, num_cores=1, property=None):
        self.num_nodes=num_nodes
        self.num_cores=num_cores
        self.property=property
    def __repr__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class ClusterInfo(object):
    def __init__(self, workernodes=[], queued_jobs=[], total_queued_job_number=0):
        self.worker_nodes=workernodes
        self.queued_jobs=queued_jobs
        self.total_queued_job_number=total_queued_job_number