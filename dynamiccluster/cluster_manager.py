
import dynamiccluster.torque_utils as torque_utils
import xml.etree.ElementTree as ET
from dynamiccluster.server import WorkerNode
from dynamiccluster.server import Job
import time

class ClusterManager(object):
    def __init__(self, config, state):
        self.__state=state
        self.__config=config
    def update_worker_nodes(self, worker_node_list):
        assert 0, 'Must define update_worker_nodes'
    def query_jobs(self):
        assert 0, 'Must define query_jobs'
    
class TorqueManager(ClusterManager):
    def __init__(self, config):
        ClusterManager.__init__(self, config, {"torque":True, "maui":True})
        
    def update_worker_nodes(self, worker_node_list):
        self.__state["torque"], pbsnodes_output=torque_utils.wn_query(self.__config['pbsnodes_command'])
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
                nodes=[n for n in worker_node_list if n.hostname==node["name"]]
                if len(nodes)>0:
                    if "jobs" in node:
                        nodes[0].__jobs=node["jobs"]
                        nodes[0].__state=WorkerNode.Busy
                else:
                    new_node=WorkerNode(node["name"])
                    new_node.__num_proc=node["np"]
                    if "jobs" in node:
                        new_node.__jobs=node["jobs"]
                        new_node.__state=WorkerNode.Busy
                    else:
                        new_node.__state=WorkerNode.Idle
                    new_node.__extra_attributes={"mom_service_port": node["mom_service_port"], 
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
        self.__state["torque"], qstat_output=torque_utils.job_query(self.__config['qstat_command'])
        self.__state["maui"], diag_p_output=torque_utils.job_query(self.__config['diagnose_p_command'])
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
                if job['job_state']=="Q" and (len(self.__config['queue_to_monitor'])==0 or job['queue'] in self.__config['queue_to_monitor']):
                    job['job_priority']=-1
                    total_number_of_idle_jobs+=1
                    if self.__config['queued_job_number_to_display'] < 1 or (self.__config['queued_job_number_to_display'] > 0 and num_of_jobs<self.__config['queued_job_number_to_display']):
                        raw_queued_jobs[job_id]=job
                        num_of_jobs+=1
                elif job['job_state']=="R":
                    new_job=Job(job_id)
                    new_job.__state=Job.Running
                    running_jobs.append(new_job)
    
            lines=diagnose_output.split("\n")
            for each_line in lines[5:]:
                if not each_line.strip():
                    break
                log.notice("each_line %s"%each_line)
                items=each_line.split()
                log.notice("items %s"%items)
                job_id=items[0].strip()
                job_dict=raw_queued_jobs[job_id]
                job=Job(job_id)
                job.__name=job_dict["Job_Name"]
                job.__owner=job_dict["Job_Owner"]
                job.__state=Job.Queued
                job.__creation_time=time.localtime(job_dict['ctime'])
                job.__priority=int(items[1].strip().replace('*',''))
                queued_jobs.append(job)

            idle_jobs.sort(key=lambda job: int(job["Job_Id"].split(".")[0].split("[")[0]), reverse=False)
            if len(idle_jobs)>0:
                log.notice("idle_jobs %d" % len(idle_jobs))
                
            return total_number_of_idle_jobs, idle_jobs, running_jobs
        except:
            log.exception("cannot parse qstat output: %s" % qstat_output)
            return 0, [], []
            