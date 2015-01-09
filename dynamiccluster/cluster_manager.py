from __future__ import absolute_import

from dynamiccluster.data import WorkerNode
from dynamiccluster.data import ProcRequirement
from dynamiccluster.data import Job
import dynamiccluster.torque_utils as torque_utils
import xml.etree.ElementTree as ET
import time
from dynamiccluster.utilities import getLogger

log = getLogger(__name__)

class ClusterManager(object):
    def __init__(self, config, state):
        self.config=config
        self.state=state
    def get_state(self):
        return self.state
    def get_config(self):
        return self.config
    def update_worker_nodes(self, worker_node_list):
        assert 0, 'Must define update_worker_nodes'
    def query_jobs(self):
        assert 0, 'Must define query_jobs'
    def add_node_to_cluster(self, node, reservation):
        assert 0, 'Must define add_node_to_cluster'
    def remove_node_from_cluster(self, node):
        assert 0, 'Must define remove_node_from_cluster'
    
class TorqueManager(ClusterManager):
    def __init__(self, config):
        ClusterManager.__init__(self, config, {"torque":True, "maui":True})
        
    def update_worker_nodes(self, worker_node_list):
        self.state["torque"], pbsnodes_output=torque_utils.wn_query(self.config['pbsnodes_command'])
        if len(pbsnodes_output)==0:
            log.debug("There is no worker node in the queue.")
            return
        try:
            root = ET.fromstring(pbsnodes_output)
            for raw_node in root.findall('Node'):
                node = {}
                for child in raw_node:
                    if child.text is None:
                        parent_name=child.tag
                        for grand_child in child:
                            node[parent_name+'.'+grand_child.tag]=grand_child.text
                    else:
                        node[child.tag]=child.text
                #if not config.node_property or ('properties' in node and node['properties'].find(config.node_property)>-1):
                #print worker_node_list
                nodes=[n for n in worker_node_list if n.hostname==node["name"]]
                if len(nodes)>0:
                    if "jobs" in node:
                        nodes[0].jobs=node["jobs"]
                        if nodes[0].state!=WorkerNode.Busy:
                            nodes[0].state_start_time=int(time.time())
                            nodes[0].state=WorkerNode.Busy
                    else:
                        if nodes[0].state!=WorkerNode.Idle:
                            nodes[0].jobs=None
                            nodes[0].state=WorkerNode.Idle
                            nodes[0].state_start_time=int(time.time())
                else:
                    new_node=WorkerNode(node["name"])
                    new_node.num_proc=int(node["np"])
                    if "Account_Name" in node:
                        new_node.account_string=node["Account_Name"]
                    if "jobs" in node:
                        new_node.jobs=node["jobs"]
                        new_node.state=WorkerNode.Busy
                    else:
                        new_node.state=WorkerNode.Idle
                    new_node.state_start_time=int(time.time())
                    new_node.extra_attributes={"mom_service_port": node["mom_service_port"], 
                                                 "mom_manager_port": node["mom_manager_port"],
                                                 "gpus": node["gpus"], "status": node["status"], "ntype": node["ntype"]}
                    worker_node_list.append(new_node)
            if len(nodes)>0:
                log.notice("nodes %d" % len(nodes))
            return 
        except:
            log.exception("can't parse pbsnodes output: %s"%pbsnodes_output)
            return 

    def query_jobs(self):
        self.state["torque"], qstat_output=torque_utils.job_query(self.config['qstat_command'])
        self.state["maui"], diag_p_output=torque_utils.job_query(self.config['diagnose_p_command'])
        if len(qstat_output)==0:
            log.debug("There is no job in the queue.")
            return [], 0
        try:
            queued_jobs = []
            running_jobs = []
            num_of_jobs = 0
            total_number_of_idle_jobs = 0
    
            root = ET.fromstring(qstat_output)
            raw_queued_jobs={}
            for raw_job in root.findall('Job'):
                job = {}
                for child in raw_job:
                    if child.text is None:
                        parent_name=child.tag
                        for grand_child in child:
                            job[parent_name+'.'+grand_child.tag]=grand_child.text
                    else:
                        job[child.tag]=child.text
                job_id=job["Job_Id"].strip().split(".")[0]
                if job['job_state']=="Q" and (len(self.config['queue_to_monitor'])==0 or job['queue'] in self.config['queue_to_monitor']):
                    job['job_priority']=-1
                    total_number_of_idle_jobs+=1
                    if self.config['queued_job_number_to_display'] < 1 or (self.config['queued_job_number_to_display'] > 0 and num_of_jobs<self.config['queued_job_number_to_display']):
                        raw_queued_jobs[job_id]=job
                        num_of_jobs+=1
                elif job['job_state']=="R":
                    new_job=Job(job_id)
                    new_job.state=Job.Running
                    running_jobs.append(new_job)
        except:
            log.exception("cannot parse qstat output: %s" % qstat_output)
            return [], 0
    
        try:
            lines=diag_p_output.split("\n")
            for each_line in lines[5:]:
                if not each_line.strip():
                    break
                #log.notice("each_line %s"%each_line)
                items=each_line.split()
                #log.notice("items %s"%items)
                job_id=items[0].strip()
                job_dict=raw_queued_jobs[job_id]
                job=Job(job_id)
                job.name=job_dict["Job_Name"]
                job.owner=job_dict["Job_Owner"]
                job.queue=job_dict["queue"]
                job.requested_walltime=job_dict["Resource_List.walltime"]
                job.requested_mem=job_dict["Resource_List.mem"]
                if "Resource_List.nodes" in job_dict:
                    strs=job_dict["Resource_List.nodes"].split(":")
                    num_cores=1
                    num_nodes=1
                    property=None
                    if len(strs)>=1:
                        if strs[0].isdigit():
                            num_nodes=int(strs[0])
                    if len(strs)>=2:
                        if "ppn=" in strs[1]:
                            nums=strs[1].split("=")
                            if len(nums)==2 and nums[1].isdigit():
                                num_cores=int(nums[1])
                            #for i in range(int(nums[0])):
                            #    vcpus.append(int(nums[1]))
                        else:
                            property=strs[1]
                    if len(strs)>2:
                        property=strs[2]
                    job.requested_proc=ProcRequirement(num_nodes, num_cores, property)
                elif "Resource_List.ncpus" in job_dict:
                    job.requested_proc=ProcRequirement(1, int(job_dict["Resource_List.ncpus"]))
                elif "Resource_List.nodes" not in job_dict and "Resource_List.ncpus" not in job_dict:
                    job.requested_proc=ProcRequirement()
                job.requested_mem=job_dict["Resource_List.mem"]
                job.state=Job.Queued
                job.creation_time=job_dict['ctime']
                job.priority=int(items[1].strip().replace('*',''))
                job.extra_attributes={"submit_host":job_dict["submit_host"], "Variable_List":job_dict["Variable_List"],
                                      "submit_args":job_dict["submit_args"]}
                queued_jobs.append(job)
                
            return queued_jobs, total_number_of_idle_jobs
        except:
            log.exception("cannot parse diagnose_p output: %s" % diag_p_output)
            return [], 0
            
    def add_node_to_cluster(self, wn, reservation):
        log.debug("adding node %s to cluster with reservation %s" % (wn, reservation))
        retry=5
        while retry>0:
            ret=torque_utils.add_node_to_torque(wn, self.config['add_node_command'])
            if ret:
                break
            retry-=1
            time.sleep(1)
        if not ret:
            log.error("cannot add %s to torque, delete it" % vm.hostname)
            return False
        #check if the new VM is added to torque
        retry=60
        while retry>0:
            node_state, s = torque_utils.check_node(wn, self.config['check_node_command'])
            if node_state is not None:
                break
            retry-=1
            log.debug("vm %s is not showing in maui yet" % wn.hostname)
            time.sleep(1)
        if node_state is None:
            log.error("cannot see %s in maui, delete it" % wn.hostname)
            torque_utils.remove_node_from_torque(wn, self.config['remove_node_command'])
            return False
        torque_utils.set_np(wn, self.config['set_node_command'])
        time.sleep(2)
        # set account string to wn
        if "queue" in reservation:
            torque_utils.set_res_for_node(wn, "queue", reservation['queue'], self.config['setres_command'])
        if "account" in reservation:
            torque_utils.set_res_for_node(wn, "account", reservation['account'], self.config['setres_command'])
        if "property" in reservation:
            torque_utils.set_node_property(wn, reservation['property'])
            time.sleep(2)
        torque_utils.set_node_online(wn, self.config['set_node_command'])
        time.sleep(2)
        return True
    