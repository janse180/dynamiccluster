from dynamiccluster.worker import Task
from dynamiccluster.utilities import getLogger
import math

log = getLogger(__name__)

class ResourceAllocator(object):
    def __init__(self, allocator="simple"):
        self.allocate=self.simple_allocate
        
    def simple_allocate(self, jobs, resources, worker_nodes):
        #log.debug("allocate new worker nodes to queued jobs")
        pending_jobs=[j for j in jobs if j.priority!=-1]
        pending_jobs.sort(key=lambda job: job.priority, reverse=True)
        tasks=[]
        for job in pending_jobs:
            avail_resources=set()
            if job.queue is not None:
                avail_resources=avail_resources&set([r for r in avail_resources if r.reservation_queue is None or r.reservation_queue==job.queue])
            if job.account is not None:
                avail_resources=avail_resources&set([r for r in avail_resources if r.reservation_account is None or r.reservation_account==job.account])
            if job.property is not None:
                avail_resources=avail_resources&set([r for r in avail_resources if r.reservation_property is None or r.reservation_property==job.property])
            avail_resources=avail_resources&set([r for r in avail_resources if r.reservation_property is None or r.reservation_property==job.property])
            if len(avail_resources)==0:
                log.notice("cannot find a suitable resource for job %s" % job.jobid)
                continue
            prioritized_resources=sorted(avail_resources, key=lambda r: (r.priority, r.current_num))
            avail_resources=[]
            special_ids=[]
            for idx, r in enumerate(prioritized_resources):
                if r.reservation_account==job.account or r.reservation_property==job.property or r.reservation_queue==job.queue:
                    special_ids.append(idx)
            for id in reversed(special_ids):
                avail_resources.insert(0, prioritized_resources.pop(id))
            avail_resources.extend(prioritized_resources)
            log.debug("avail_resources %s"%[r.name for r in avail_resources])
            for res in avail_resources:
                if res.proposed_allocation is None:
                    res.proposed_allocation=[]
                if self.can_fit(job, res):
                    break
        for res in resources:
            if res.proposed_allocation is not None and len(res.proposed_allocation)>0:
                log.debug("res %s allocation %s"%(res.name, res.proposed_allocation))
                tasks.append(Task(Task.Provision, {"resource": res, "number": len(res.proposed_allocation)}))
                res.proposed_allocation=None
        return tasks
    
    def can_fit(self, job, res):
        if job.cores_per_node>res.cores_per_node:
            return False
        cores_left=(res.max_num-res.current_num)*res.cores_per_node-sum(i for i in res.proposed_allocation)
        if cores_left<job.requested_cores:
            return False
        if job.cores_per_node==0:
            requested_cores=job.requested_cores
            #fill up existing ones first
            for i in range(len(res.proposed_allocation)):
                if res.proposed_allocation[i]<res.cores_per_node:
                    requested_cores-=(res.cores_per_node-res.proposed_allocation[i])
                    res.proposed_allocation[i]=res.cores_per_node
            while requested_cores>0:
                if requested_cores>=res.cores_per_node:
                    res.proposed_allocation.append(res.cores_per_node)
                    requested_cores-=res.cores_per_node
                else:
                    res.proposed_allocation.append(requested_cores)
                    requested_cores=0
            log.notice("job %s fits in res %s allocation %s" % (job.jobid, res.name, res.proposed_allocation))
            return True
        num_nodes=int(math.ceil(job.requested_cores/job.cores_per_node))
        if num_nodes > res.max_num-res.current_num:
            return False
        avail_num_nodes = res.max_num-res.current_num-sum(1 for i in res.proposed_allocation if res.cores_per_node-i<job.cores_per_node)
        if avail_num_nodes < num_nodes:
            return False
        log.notice("job %s num_nodes %s"%(job.jobid, num_nodes))
        for i in range(len(res.proposed_allocation)):
            if res.proposed_allocation[i]+job.cores_per_node<=res.cores_per_node:
                res.proposed_allocation[i]+=job.cores_per_node
                num_nodes-=1
                if num_nodes==0:
                    break
        while num_nodes>0:
            res.proposed_allocation.append(job.cores_per_node)
            num_nodes-=1
        log.notice("job %s fits in res %s allocation %s" % (job.jobid, res.name, res.proposed_allocation))
        return True
        