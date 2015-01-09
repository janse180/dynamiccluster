from dynamiccluster.utilities import get_unique_string, load_template_with_jinja, getLogger, hostname_lookup
from dynamiccluster.data import Instance
import time
from novaclient.v1_1 import client
from novaclient.exceptions import NotFound
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
    def update(self, **kwargs):
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
                instance.state=self.get_state(server)
                log.debug("launched a new instance: %s"%instance)
                new_instances.append(instance)
            except:
                log.exception("Unable to boot a new instance.")
                pass
        if len(new_instances)==0:
            raise CloudNotAvailableException()
        return new_instances
    
    def update(self, instance):
        log.notice("Getting instance %s..." % (instance.uuid))
        try:
            server = self.__conn.servers.get(instance.uuid)
        except NotFound:
            log.info("instance %s doesn't exist"%uuid)
            instance.state=Instance.Inexistent
            return instance
        except:
            log.exception("Unable to get instance details.")
            raise CloudNotAvailableException()
        instance.state=self.get_state(server)
        log.debug("instance %s; Cloud Status: %s; State: %s" % (server.id,server.status, instance.state))
        instance.creation_time=server.created
        if instance.vcpu_number == 0:
            try:
                instance.vcpu_number=self.__conn.flavors.get(server.flavor['id']).vcpus
            except:
                log.exception("Unable to get flavor for instance %s"%instance.uuid)
        if instance.state==Instance.Active:
            try:
                ip=server.addresses.values()[0][0]['addr']
                if instance.public_dns_name==None:
                    instance.public_dns_name=hostname_lookup(ip)
            except:
                log.exception("Unable to get IP for instance %s"%instance.uuid)
                instance.state=Instance.Starting
                return instance
            instance.availability_zone=getattr(server,"OS-EXT-AZ:availability_zone")
            instance.image_id=server.image['id']
            instance.ip=ip
        return instance
        
    def get_flavor_id(self, flavor):
        try:
            flavor_list=self.__conn.flavors.list()
            for f in flavor_list:
                if f.name==flavor:
                    return f.id
        except:
            log.exception("Encounter an error when getting flavor list.")
        raise FlavorNotFoundException()
    
    def get_state(self, server):
        if server.status == "ERROR" or getattr(server,"OS-EXT-STS:vm_state") == "error":
            return Instance.Error
        elif server.status == "ACTIVE":
            return Instance.Active
        elif server.status == "DELETING" or getattr(server,"OS-EXT-STS:task_state") == "Deleting":
            return Instance.Active
        elif server.status != "ACTIVE" or getattr(server,"OS-EXT-STS:vm_state") != "active" or getattr(server,"OS-EXT-STS:task_state") is not None:
            return Instance.Starting
        log.info("instance %s is in a strange state: status %s, vm_state %s, task_state %s" % (server.id, server.status, getattr(server,"OS-EXT-STS:vm_state"), getattr(server,"OS-EXT-STS:task_state")))
        return Instance.Unknown
        
class AWSManager(CloudManager):
    def __init__(self, config):
        CloudManager.__init__(self, config)


class CloudNotAvailableException(BaseException):
    pass

class FlavorNotFoundException(BaseException):
    pass