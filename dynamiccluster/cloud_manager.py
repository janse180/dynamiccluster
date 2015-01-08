from dynamiccluster.utilities import get_unique_string, load_template_with_jinja, getLogger
from dynamiccluster.data import Instance
import time
from novaclient.v1_1 import client
import os

log = getLogger(__name__)

class CloudManager(object):
    def __init__(self, name, config, max_attempt_time=5):
        self.name=name
        self.config=config
        self.max_attempt_time=max_attempt_time
        
    def list(self, **kwargs):
        assert 0, 'Must define list'
    def boot(self, **kwargs):
        assert 0, 'Must define boot'
    def destroy(self, **kwargs):
        assert 0, 'Must define boot'
    def get(self, **kwargs):
        assert 0, 'Must define get'
    
    
class OpenStackManager(CloudManager):
    def __init__(self, name, config, max_attempt_time=5):
        CloudManager.__init__(self, name, config, max_attempt_time)
        self.__conn=self._connect()
    def _connect(self):
        log.debug("Opening connection to OpenStack for %s of %s." % (self.config['username'],self.config['project']))
        connected=False
        attempt_time=0
        while not connected:
            try:
                conn=client.Client(self.config['username'], self.config['password'], self.config['project'], self.config['auth_url'])
                conn.authenticate()
                connected=True
            except:
                log.exception("Encounter an error when connecting to OpenStack.")
                attempt_time+=1
                if attempt_time>=self.max_attempt_time:
                    raise CloudNotAvailableException()
                time.sleep(5)
        return conn
    def boot(self, number=1):
        """ Start new instance (used by active mode only) """
        try:
            flavor_obj=self.__conn.flavors.get(self.config['flavor_id'])
            log.debug("flavor %s; availability_zone %s; image-uuid %s; userdata %s;" % (flavor_obj, self.config['availability_zone'], self.config['image_uuid'], self.config['userdata_file']))
        except:
            log.exception("Unable to get flavor.")
            raise CloudNotAvailableException()

        new_instances=[]
        for i in xrange(number):
            try:
                server_name=self.config['instance_name_prefix']+"-"+get_unique_string()
                if os.path.exists(self.config['userdata_file']) and os.path.isfile(self.config['userdata_file']):
                    userdata_string=load_template_with_jinja(self.config['userdata_file'], {"minion_id":server_name})
                else:
                    log.exeception("userdata file does not exist, can't create VM, please check your config.")
                    return None
                server = self.__conn.servers.create(server_name, self.config['image_uuid'], flavor_obj, key_name=self.config['key_name'], max_count=1, min_count=1, userdata=userdata_string, security_groups=self.config['security_groups'], availability_zone=self.config['availability_zone']) #scheduler_hints={'cell':self.default_availability_zone})
                instance = Instance(server.id)
                instance.instance_name=server_name
                instance.vcpu_number=flavor_obj.vcpus
                instance.creation_time=server.created
                instance.key_name=self.config['key_name']
                instance.flavor=self.config['flavor']
                instance.security_groups=self.config['security_groups']
                instance.availability_zone=self.config['availability_zone']
                instance.image_uuid=self.config['image_uuid']
                instance.cloud_resource=self.name
                log.debug("launched a new instance: %s"%instance)
                new_instances.append(instance)
            except:
                log.exception("Unable to boot a new instance.")
                pass
        if len(new_instances)==0:
            raise CloudNotAvailableException()
        return new_instances
        
    def get_flavor_id(self, flavor):
        try:
            flavor_list=self.__conn.flavors.list()
            for f in flavor_list:
                if f.name==flavor:
                    return f.id
        except:
            log.exception("Encounter an error when getting flavor list.")
        raise FlavorNotFoundException()
        
class AWSManager(CloudManager):
    def __init__(self, config):
        CloudManager.__init__(self, config)


class CloudNotAvailableException(BaseException):
    pass

class FlavorNotFoundException(BaseException):
    pass