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
                if "spot_bid" in self.config:
                    #start spot
                    timeout=300
                    if "spot_timeout" in self.config:
                        timeout=self.config["spot_timeout"]
                    valid_until=(datetime.datetime.utcnow()+datetime.timedelta(0, timeout)).isoformat()
                    req=self.conn.request_spot_instances(self.config['spot_bid'], self.config['image_id'], count=1, valid_until=valid_until, user_data=userdata_string, placement=self.config['availability_zone'], instance_type=self.config['instance_type'], key_name=self.config['key_name'], security_groups=self.config['security_groups'])
                    log.debug("create spot request %s" % req)
                    if len(req)==0:
                        log.error("unable to create spot request")
                        raise CloudNotAvailableException()
                    self.conn.create_tags([req[0].id], {'Name':server_name})
                    instance = Instance(None)
                    instance.instance_name=server_name
                    instance.key_name=self.config['key_name']
                    instance.flavor=self.config['instance_type']
                    instance.security_groups=self.config['security_groups']
                    instance.availability_zone=self.config['availability_zone']
                    instance.image_uuid=self.config['image_id']
                    instance.cloud_resource=self.name
                    instance.state=Instance.Pending
                    instance.spot_id=req[0].id
                    instance.spot_state=req[0].state
                    instance.spot_price=req[0].price
                    log.debug("submitted a spot request: %s"%instance)
                    new_instances.append(instance)
                else:
                    reservation = self.conn.run_instances(self.config['image_id'], key_name=self.config['key_name'], max_count=1, min_count=1, user_data=userdata_string, security_groups=self.config['security_groups'], instance_type=self.config['instance_type'], placement=self.config['availability_zone']) 
                    for server in reservation.instances:
                        server.add_tag('Name', server_name)
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
        server=None
        if instance.spot_id is not None and instance.uuid==None:
            log.notice("Updating spot request %s..." % (instance.spot_id))
            try:
                requests = self.conn.get_all_spot_instance_requests(request_ids=[instance.spot_id])
                if len(requests)==0 or requests[0].state in ["closed", "canceled", "failed"]:
                    instance.state=WorkerNode.Inexistent
                    return instance
                else:
                    instance.spot_state=requests[0].state
                    if requests[0].state=="active":
                        servers = self.conn.get_only_instances(filters={"instance-id": requests[0].instance_id})
                        if len(servers)==0:
                            log.debug("instance %s doesn't exist yet"%requests[0].instance_id)
                        else:
                            server=servers[0]
                            log.debug("instance %s is created as spot instance"%requests[0].instance_id)
                            tags=self.conn.get_all_tags(filters={"resource-id":requests[0].id, "tag-key":"Name"})
                            if len(tags)>0 and tags[0].name=="Name":
                                server.add_tag('Name', tags[0].value)
                            instance.uuid=requests[0].instance_id
                            instance.vcpu_number=get_aws_vcpu_num_by_instance_type(server.instance_type)
                            instance.creation_time=unix_time(datetime.datetime.strptime(server.launch_time, "%Y-%m-%dT%H:%M:%S.%fZ"))
            except:
                log.exception("Unable to get spot request details.")
                raise CloudNotAvailableException()
        if instance.uuid is not None and server is None:
            log.notice("Getting instance %s..." % (instance.uuid))
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
        if server is not None:
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
            instances = []
            requests = self.conn.get_all_spot_instance_requests(filters={"tag:Name":self.config['instance_name_prefix']+"-*", "state":["open","active"]})
            spot_ids=[]
            for request in requests:
                instance = Instance(None)
                if request.instance_id is not None:
                    instance.uuid=request.instance_id
                tags=self.conn.get_all_tags(filters={"resource-id":request.id, "tag-key":"Name"})
                if len(tags)>0 and tags[0].name=="Name":
                    instance.instance_name=tags[0].value
                instance.key_name=self.config['key_name']
                instance.flavor=self.config['instance_type']
                instance.security_groups=self.config['security_groups']
                instance.availability_zone=self.config['availability_zone']
                instance.image_uuid=self.config['image_id']
                instance.cloud_resource=self.name
                instance.state=Instance.Pending
                instance.spot_id=request.id
                instance.spot_state=request.state
                instance.spot_price=request.price
                instances.append(instance)
                spot_ids.append(request.id)
            servers = self.conn.get_only_instances(filters={"tag:Name":self.config['instance_name_prefix']+"-*"})
            for server in servers:
                instance=None
                if server.spot_instance_request_id is not None and server.spot_instance_request_id in spot_ids:
                    log.debug("instance %s has been created in the past 2 seconds!" % server.id)
                    ins=[i for i in instances if i.spot_id==server.spot_instance_request_id]
                    if len(ins)==0:
                        log.debug("...but it is not in the list... strange...")
                    else:
                        instance=ins[0]
                        instance.uuid=server.id
                else:
                    instance=Instance(server.id)
                    instances.append(instance)
                instance.instance_name=server.tags['Name']
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
            return instances
        except:
            log.exception("Encounter an error when connecting to AWS.")
            return []

    def destroy(self, instance):
        """ Terminate an instance """
        log.debug("Destroying instance %s (ip=%s)"%(instance.uuid,instance.ip))
        try:
            if instance.uuid is not None:
                self.conn.terminate_instances(instance_ids=[instance.uuid])
            if instance.spot_id is not None:
                self.conn.cancel_spot_instance_requests([instance.spot_id])
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