from dynamiccluster.worker import Task
from dynamiccluster.utilities import getLogger

log = getLogger(__name__)

class ResourceAllocator(object):
    def __init__(self, allocator="simple"):
        self.allocate=self.simple_allocate
        
    def simple_allocate(self, jobs, resources, worker_nodes):
        #log.debug("allocate new worker nodes to queued jobs")
        for job in jobs:
            pass
        return []