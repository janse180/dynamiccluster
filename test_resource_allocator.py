import unittest
import copy

#sys.path.append('..')
from dynamiccluster.resource_allocator import ResourceAllocator
from dynamiccluster.data import Job, CloudResource

class ResourceAllocatorTestCase(unittest.TestCase):
    def setUp(self):
        job=Job('417')
        job.priority=0
        job.name=''
        job.queue="default"
        job.account=None
        job.property=None
        job.requested_mem=None
        job.requested_cores=1
        job.cores_per_node=1
        job.requested_walltime="00:50:00"
        job.creation_time=1441174461
        self.job1=job
        job2 = copy.deepcopy(job)
        job2.account='account'
        self.job2=job2
        res1=CloudResource("res-all", type="openstack", priority=1, quantity={'min':1, 'max':3}, config=None, reservation={'account': None, 'queue': None, 'property': None})
        res1.cores_per_node=1
        self.res1=res1
        res2=CloudResource("res-account", type="openstack", priority=1, quantity={'min':1, 'max':10}, config=None, reservation={'account': 'account', 'queue': None, 'property': None})
        res2.cores_per_node=1
        self.res2=res2
    
    def test_simple_allocator(self):
        allocator=ResourceAllocator()
        res1={"name": "res-all", "proposed_allocation": [], "type": "openstack", "worker_nodes": [], "priority": 1, "reservation_property": "cloud", "reservation_account": None, "cores_per_node": 1, "current_num": 3, "min_num": 1, "config": {}, "max_num": 3, "reservation_queue": None}
        res2={"name": "res-account", "proposed_allocation": [], "type": "openstack", "worker_nodes": [], "priority": 2, "reservation_property": "cloud", "reservation_account": "account", "cores_per_node": 1, "current_num": 7, "min_num": 1, "config": {}, "max_num": 10, "reservation_queue": None}
        resources=[self.res1, self.res2]
        worker_nodes=[]
        self.assertTrue(allocator.match(self.job1, self.res1))
        self.assertFalse(allocator.match(self.job1, self.res2))
        self.assertTrue(set([r.name for r in allocator.get_available_resources(self.job1, resources)])==set(['res-all']))
        self.assertTrue(set([r.name for r in allocator.get_available_resources(self.job2, resources)])==set(['res-all', 'res-account']))
        self.assertTrue(set([t.data['resource'].name for t in allocator.allocate([self.job1], resources, worker_nodes)])==set(['res-all']))
        self.assertTrue(set([t.data['resource'].name for t in allocator.allocate([self.job2], resources, worker_nodes)])==set(['res-account']))

if __name__ == '__main__':
    unittest.main()
