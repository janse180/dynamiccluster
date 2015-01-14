from dynamiccluster.utilities import get_unique_string, load_template_with_jinja, getLogger, hostname_lookup, unix_time, get_aws_vcpu_num_by_instance_type
from dynamiccluster.data import Instance
from dynamiccluster.exceptions import CloudNotAvailableException, FlavorNotFoundException
from dynamiccluster.cloud_manager import CloudManager
import time
import datetime
import os
import boto
import boto.ec2 as ec2
from boto import config as boto_config
from boto.connection import HAVE_HTTPS_CONNECTION
from boto.s3.key import Key

log = getLogger(__name__)

class AWSManager(CloudManager):
    def __init__(self, config, max_attempt_time=5):
        CloudManager.__init__(self, config, max_attempt_time)
        self.__conn=None
        
    @property
    def conn(self):
        if self.__conn is None:
            log.debug('creating ec2 connection to %s' % self.config['region_name'])
            validate_certs = self.config['validate_certs']
            if validate_certs:
                if not HAVE_HTTPS_CONNECTION:
                    raise CloudNotAvailableException(
                        "Failed to validate AWS SSL certificates. "
                        "SSL certificate validation is only supported "
                        "on Python>=2.6.\n\nSet AWS_VALIDATE_CERTS=False in "
                        "your config to skip SSL certificate verification and"
                        " suppress this error AT YOUR OWN RISK.")
            if not boto_config.has_section('Boto'):
                boto_config.add_section('Boto')
            # Hack to get around the fact that boto ignores validate_certs
            # if https_validate_certificates is declared in the boto config
            boto_config.setbool('Boto', 'https_validate_certificates',
                                validate_certs)
            #boto_config.setint('Boto', 'http_socket_timeout',
            #                    10)
            kwargs=dict(aws_access_key_id=self.config['access_key_id'], aws_secret_access_key=self.config['secret_access_key'],
                validate_certs=self.config['validate_certs'])
            if self.config['proxy']:
                kwargs['proxy']=self.config['proxy']
                kwargs['proxy_port']=self.config['proxy_port']
            self.__conn = ec2.connect_to_region(self.config['region_name'], **kwargs)
            self.__conn.https_validate_certificates = validate_certs
        return self.__conn

    def boot(self, number=1):
        """ Start new instance """
        new_instances=[]
        for i in xrange(number):
            try:
                server_name=self.config['instance_name_prefix']+"-"+get_unique_string()
                if os.path.exists(self.config['userdata_file']) and os.path.isfile(self.config['userdata_file']):
                    userdata_string=load_template_with_jinja(self.config['userdata_file'], {"minion_id":server_name})
                else:
                    log.exeception("userdata file does not exist, can't create VM, please check your config.")
                    return None
                reservation = self.conn.run_instances(self.config['image_id'], key_name=self.config['key_name'], max_count=1, min_count=1, user_data=userdata_string, security_groups=self.config['security_groups'], instance_type=self.config['instance_type'], placement=self.config['availability_zone']) 
                for server in reservation.instances:
                    server.add_tag('name', server_name)
                    instance = Instance(server.id)
                    instance.instance_name=server_name
                    instance.vcpu_number=get_aws_vcpu_num_by_instance_type(server.instance_type)
                    instance.creation_time=unix_time(datetime.datetime.strptime(server.launch_time, "%Y-%m-%dT%H:%M:%S.%fZ"))
                    instance.key_name=self.config['key_name']
                    instance.flavor=self.config['instance_type']
                    instance.security_groups=self.config['security_groups']
                    instance.availability_zone=self.config['availability_zone']
                    instance.image_uuid=self.config['image_id']
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
        server=None
        try:
            servers = self.conn.get_only_instances(filters={"instance-id": instance.uuid})
            if len(servers)==0:
                log.info("instance %s doesn't exist"%instance.uuid)
                instance.state=Instance.Inexistent
                return instance
            server=servers[0]
        except:
            log.exception("Unable to get instance details.")
            raise CloudNotAvailableException()
        instance.state=self.get_state(server)
        log.debug("instance %s; Cloud Status: %s; State: %s" % (server.id, server.state, instance.state))
        instance.creation_time=unix_time(datetime.datetime.strptime(server.launch_time, "%Y-%m-%dT%H:%M:%S.%fZ"))
        instance.vcpu_number=get_aws_vcpu_num_by_instance_type(server.instance_type)
        if instance.state==Instance.Active:
            instance.ip=server.ip_address
            instance.public_dns_name=server.public_dns_name
            instance.availability_zone=server.placement
            instance.image_uuid=server.image_id
        return instance

    def list(self):
        """ List all instances with the configured prefix """
        try:
            servers = self.conn.get_only_instances(filters={"tag:name":self.config['instance_name_prefix']+"-*"})
            instances = []
            for server in servers:
                instance=Instance(server.id)
                instance.instance_name=server.tags['name']
                instance.creation_time=unix_time(datetime.datetime.strptime(server.launch_time, "%Y-%m-%dT%H:%M:%S.%fZ"))
                instance.key_name=server.key_name
                instance.flavor=server.instance_type
                sec_groups=[]
                for group in server.groups:
                    sec_groups.append(group.name)
                instance.security_groups=sec_groups
                instance.availability_zone=server.placement
                instance.image_uuid=server.image_id
                instance.cloud_resource=self.name
                instance.state=self.get_state(server)
                if instance.state == Instance.Active:
                    instance.ip=server.ip_address
                    instance.public_dns_name=server.public_dns_name
                instance.vcpu_number=get_aws_vcpu_num_by_instance_type(server.instance_type)
                instances.append(instance)
            return instances
        except:
            log.exception("Encounter an error when connecting to AWS.")
            return []

    def destroy(self, instance):
        """ Terminate an instance """
        log.debug("Destroying instance %s (ip=%s)"%(instance.uuid,instance.ip))
        try:
            servers = self.conn.terminate_instances(instance_ids=[instance.uuid])
            #vm.delete_time = datetime.datetime.utcnow()
        #except NotFound as ex:
        #    log.debug("instance %s is already shut down"%(instance.uuid))
            #vm.delete_time = datetime.datetime.utcnow()
        except:
            log.exception("Encounter an error when connecting to AWS.")
            return False
        # ensure the server's state is indeed changed to deleting or deleted
        return True

    def get_state(self, server):
        """
        convert boto states to our states
        
        * 0 (pending)
        * 16 (running)
        * 32 (shutting-down)
        * 48 (terminated)
        * 64 (stopping)
        * 80 (stopped)

        """
        if server.state_code==16:
            return Instance.Active
        elif server.state_code==0:
            return Instance.Starting
        elif server.state_code==32 or server.state_code==64:
            return Instance.Deleting
        elif server.state_code==48:
            return Instance.Inexistent
        return Instance.Unknown