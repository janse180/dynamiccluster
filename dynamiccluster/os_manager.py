"""
this class deals with OpenStack
"""
from dynamiccluster.utilities import get_unique_string, load_template_with_jinja, getLogger, hostname_lookup, unix_time
from dynamiccluster.data import Instance
from dynamiccluster.exceptions import CloudNotAvailableException, FlavorNotFoundException
from dynamiccluster.cloud_manager import CloudManager
import time
import os
import datetime
import sys

log = getLogger(__name__)


#try:
 #   from novaclient import client
 #   from novaclient.exceptions import NotFound
#except ImportError:
#    sys.stderr.write("python-novaclient is not installed, you won't be able to use OpenStack as your cloud resources.\n")


try: 
    from openstack import connection
    from openstack import profile
    from openstack import exceptions
    from openstack import utils
    from openstack import compute
    from openstack import network
except ImportError:
    sys.stderr.write("Cannot find the OpenStack SDK on your system, please install the OpenStack SDK before continuing (pip install openstacksdk)")



class OpenStackManager(CloudManager):
    def __init__(self, name, config, max_attempt_time=5):
        CloudManager.__init__(self, name, config, max_attempt_time)
        self.__conn = self._connect()

    def _connect(self):
        log.debug("Opening connection to OpenStack for %s of %s." % (self.config['username'],self.config['project']))
        connected=False
        attempt_time=0
        while not connected:
            try:
                #conn=client.Client(2, self.config['username'], self.config['password'], self.config['project'], self.config['auth_url'])
                
                #Openstack Profile
                prof = profile.Profile()
                prof.set_region(prof.ALL, 'RegionOne')
                prof.set_api_version('identity', 'v3')

                #Openstack Connection
                connected=True

                return connection.Connection(
                    auth_url=self.config['auth_url'],
                    profile=prof,
                    username=self.config['username'],
                    password=self.config['password'],
                    project_name=self.config['project'],
                    user_domain_name=self.config['user_domain_name'],
                    project_domain_name=self.config['project_domain_name']
                )

            except:
                log.exception("Encounter an error when connecting to OpenStack.")
                attempt_time+=1
                if attempt_time>=self.max_attempt_time:
                    raise CloudNotAvailableException()
                time.sleep(5)

        return conn
    

    #def test_connection(self):
       # return self.__conn.network.find_network("Test")

    def boot(self, number=1):
        """ Start new instance (used by active mode only) """

        new_instances=[]
        for i in xrange(number):
            #Try to boot an instance
            try:
                #Setup Server Name
                server_name=self.config['instance_name_prefix']+"-"+get_unique_string()
                #Verify User Data file Exists
                if os.path.exists(self.config['userdata_file']) and os.path.isfile(self.config['userdata_file']):
                    #userdata_string=load_template_with_jinja(self.config['userdata_file'], {"minion_id":server_name})
                    userdata_string="test"
                else:
                    log.exception("userdata file does not exist, can't create VM, please check your config.")
                    return None
                
                flavor = self.__conn.compute.find_flavor(self.config['flavor_id'])
                
                #Server Args
                kwargs={
                    "key_name": self.config['key_name'],
                    "max_count": 1, 
                    "min_count": 1,
                    "userdata": userdata_string,
                    "security_groups": self.config['security_groups'],
                    "image_id": self.config['image_uuid'],
                    "flavor_id": flavor.id,
                    #"availability_zone": "nova",
                    "name": server_name
                    }
               # if 'availability_zone' in self.config:
                #    kwargs['availability_zone']=self.config['availability_zone']
                    
                ##server = self.__conn.servers.create(server_name, self.config['image_uuid'], flavor_obj, **kwargs) #scheduler_hints={'cell':self.default_availability_zone})
                
                #Create Server
                server = self.__conn.compute.create_server(**kwargs)

                instance = Instance(server.id)
                instance.instance_name=server_name
                instance.vcpu_number=flavor.vcpus
                instance.creation_time=server.created_at
                instance.key_name=self.config['key_name']
                instance.flavor=flavor.name
                instance.security_groups=self.config['security_groups']
                #if 'availability_zone' in self.config:
                 #   instance.availability_zone=self.config['availability_zone']
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
        """
        update status of instance
        """
        log.notice("Getting instance %s..." % (instance.uuid))
        try:
            server = self.__conn.servers.get(instance.uuid)
        except NotFound:
            log.info("instance %s doesn't exist"%instance.uuid)
            instance.state=Instance.Inexistent
            return instance
        except:
            log.exception("Unable to get instance details.")
            raise CloudNotAvailableException()
        instance.state=self.get_state(server)
        log.debug("instance %s; Cloud Status: %s; State: %s" % (server.id,server.status, instance.state))
        instance.creation_time=unix_time(datetime.datetime.strptime(server.created, "%Y-%m-%dT%H:%M:%SZ"))
        if instance.vcpu_number == 0:
            try:
                instance.vcpu_number=self.__conn.flavors.get(server.flavor['id']).vcpus
            except:
                log.exception("Unable to get flavor for instance %s"%instance.uuid)
        if instance.state==Instance.Active:
            try:
                ip=server.addresses.values()[0][0]['addr']
                if instance.dns_name==None:
                    instance.dns_name=hostname_lookup(ip)
            except:
                log.exception("Unable to get IP for instance %s"%instance.uuid)
                instance.state=Instance.Starting
                return instance
            instance.availability_zone=getattr(server,"availability_zone")
            instance.image_uuid=server.image['id']
            instance.ip=ip
        return instance


    def list(self):
        """ List all instances with the configured prefix """
        try:
            
            servers = self.__conn.compute.servers(**{"name":self.config['instance_name_prefix']+"-*"})
            instances = []
            for server in servers:
                instance=Instance(server.id)
                instance.instance_name=server.name
                instance.creation_time=server.created_at
                instance.key_name=self.config['key_name']
                instance.flavor=self.config['flavor_id']
                instance.security_groups=self.config['security_groups']
                instance.availability_zone=self.config['availability_zone']
                instance.image_uuid=server.image['id']
                instance.cloud_resource=self.name
                instance.state=self.get_state(server)
                if instance.state == Instance.Active:
                    try:
                        log.notice("ip1 %s"%server.addresses.values())
                        log.notice("ip2 %s"%server.addresses.values()[0])
                        log.notice("ip3 %s"%server.addresses.values()[0][0])
                        instance.ip=server.addresses.values()[0][0]['addr']
                        instance.dns_name=hostname_lookup(instance.ip)
                    except:
                        log.exception("Unable to get IP for instance %s"%instance)
                    instance.availability_zone=getattr(server,"availability_zone")
                    instance.image_uuid=server.image['id']
                os_flavor=self.__conn.compute.find_flavor(server.flavor['id'])
                instance.vcpu_number=os_flavor.vcpus
                instances.append(instance)
            return instances
        except:
            log.exception("Encounter an error when connecting to OpenStack.")
            return []


    def destroy(self, instance):
        """ Terminate an instance """
        log.debug("Destroying instance %s (ip=%s)"%(instance.uuid,instance.ip))
        try:
            server = self.__conn.compute.find_server(instance.uuid)
            self.__conn.compute.delete_server(server,True)
            #vm.delete_time = datetime.datetime.utcnow()
        except exceptions.ResourceNotFound as ex:
            log.debug("instance %s is already shut down"%(instance.uuid))
            #vm.delete_time = datetime.datetime.utcnow()
        except:
            log.exception("Encounter an error when connecting to OpenStack.")
            return False
        # ensure the server's state is indeed changed to deleting or deleted
        time.sleep(1)
        try:
            server = self.__conn.compute.find_server(vm.id)
            if server.status == "ACTIVE":
                time.sleep(2)
        except:
            pass
        return True


    def get_flavor_details(self, flavor):
        try:
            flavor_list=self.__conn.flavors.list()
            for f in flavor_list:
                if f.name==flavor:
                    return f.id, f.vcpus
        except:
            log.exception("Encounter an error when getting flavor list.")
        raise FlavorNotFoundException()
    

    def get_state(self, server):
        """
        convert openstack state to dynamic cluster state
        """
        if server.status == "ERROR" or getattr(server,"vm_state") == "error":
            return Instance.Error
        elif server.status == "ACTIVE":
            return Instance.Active
        elif server.status == "DELETING" or server.status == "DELETED" or (getattr(server,"task_state") is not None and getattr(server,"task_state").lower() == "deleting"):
            return Instance.Deleting
        elif server.status != "ACTIVE" or getattr(server,"vm_state") != "active" or getattr(server,"task_state") is not None:
            return Instance.Starting
        log.info("instance %s is in a strange state: status %s, vm_state %s, task_state %s" % (server.id, server.status, getattr(server,"vm_state"), getattr(server,"task_state")))
        return Instance.Unknown
