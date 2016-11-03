import unittest
import copy
import logging

log = logging.getLogger(__name__)

from dynamiccluster.os_manager import OpenStackManager
from dynamiccluster.cloud_manager import CloudManager

class OpenstackConnectionTestCase(unittest.TestCase):
    def setUp(self):
        loglevel = logging.DEBUG
        logging.basicConfig(level=loglevel)



    def test_simple_allocator(self):
        sec_groups = [{"name": '6af1fb7c-f285-4a38-849c-87124d4c1b48'}]
        config={
            'auth_url': 'https://openstack.safl.umn.edu:5000/v3',
            'username': 'janse180',
            'password': '**',
            'project': 'Interactive',
            'image_uuid': '186f27a3-8498-4b9a-9385-bab31a70b3e1',
            'flavor_id': '3',
            'key_name': 'cloud_key',
            'security_groups': sec_groups,
            'availability_zone': 'nova',
            'instance_name_prefix': 'dctest',
            'user_domain_name': 'ad',
            'project_domain_name': 'ad',
            'userdata_file': '/Users/mattj150/work/git/dynamiccluster_venv/dynamiccluster/tests/userdata.sh'
            }

        #cm = CloudManager('test', **config)
        os = OpenStackManager('test', config)
        #os.boot(5)
        instances = os.list()
        log.debug(instances)
        for instance in instances:
            os.destroy(instance)

if __name__ == '__main__':
    unittest.main()
        