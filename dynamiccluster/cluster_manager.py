from __future__ import absolute_import

from dynamiccluster.data import WorkerNode
from dynamiccluster.data import Job
import dynamiccluster.torque_utils as torque_utils
import dynamiccluster.sge_utils as sge_utils
import xml.etree.ElementTree as ET
import time
import datetime
from dynamiccluster.utilities import getLogger, unix_time
from dynamiccluster.hooks import run_post_command

log = getLogger(__name__)

class ClusterManager(object):
    def __init__(self, config, state):
        self.config=config
        self.state=state
    def get_state(self):
        """
        get cluster's state
        """
        return self.state
    def get_config(self):
        """
        get cluster's config
        """
        return self.config
    def update_worker_nodes(self, worker_node_list):
        """
        update existing worker nodes' status
        """
        assert 0, 'Must define update_worker_nodes'
    def check_reservation(self, node, reservation):
        """
        check reservation in startup, if not reserved properly, fix it
        """
        assert 0, 'Must define check_reservation'
    def query_jobs(self):
        """
        get a list of queued jobs
        """
        assert 0, 'Must define query_jobs'
    def on_instance_active(self, worker_node, reservation):
        """
        this is called once the node is provisioned by the cloud (e.g. it is booting up but IP is available at this moment)
        """
        pass
    def on_instace_ready(self, worker_node, reservation):
        """
        this is called once the node is ready (configuration finished)
        """
        pass
    def add_node(self, node, reservation):
        """
        add the node to cluster with reservation
        """
        assert 0, 'Must define add_node'
    def hold_node(self, node):
        """
        hold the node in cluster so that it won't accept new jobs, existing jobs keep running
        """
        assert 0, 'Must define hold_node'
    def unhold_node(self, node):
        """
        unhold the node in cluster and put it back to working state
        """
        assert 0, 'Must define hold_node'
    def remove_node(self, node):
        """
        remove the node from cluster
        """
        assert 0, 'Must define remove_node'
    def vacate_node(self, node):
        """
        kill all jobs on this node (so it can be removed etc)
        """
        assert 0, 'Must define vacate_node'
    
class TorqueManager(ClusterManager):
    def __init__(self, config):
        ClusterManager.__init__(self, config, {"torque":True, "maui":True})
        
    def update_worker_nodes(self, worker_node_list):
        self.state["torque"], pbsnodes_output=torque_utils.wn_query(self.config['pbsnodes_command'])
        if self.state["torque"]==False:
            return
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
                the_node=None
                if len(nodes)>0:
                    the_node=nodes[0]
                else:
                    the_node=WorkerNode(node["name"])
                    the_node.num_proc=int(node["np"])
                    if "Account_Name" in node:
                        the_node.account_string=node["Account_Name"]
                    worker_node_list.append(the_node)
                node_state, s = torque_utils.check_node(the_node, self.config['check_node_command'])
                if node_state is None:
                    log.debug("maui is down.")
                    self.state['maui']=False
                    return
                else:
                    self.state['maui']=True
                the_node.time_in_current_state=s
                the_node.state_start_time=0
                if "mom-list-not-sent" in node["state"].lower():
                    the_node.state=WorkerNode.Starting
                elif "offline" in node["state"].lower():
                    if node_state == "drained":
                        the_node.state=WorkerNode.Held
                    else:
                        the_node.state=WorkerNode.Holding
                elif "down" in node_state:
                    the_node.state=WorkerNode.Error
                elif node_state == "busy" or node_state == "running":
                    the_node.state=WorkerNode.Busy
                elif node_state == "idle":
                    the_node.state=WorkerNode.Idle
                if "jobs" in node:
                    the_node.jobs=node["jobs"]
                else:
                    the_node.jobs=None
                the_node.extra_attributes={"mom_service_port": node["mom_service_port"], 
                                             "mom_manager_port": node["mom_manager_port"],
                                             "ntype": node["ntype"]}
                if "gpus" in node:
                    the_node.extra_attributes["gpus"]=node["gpus"]
                if "properties" in node:
                    the_node.extra_attributes["properties"]=node["properties"]
                if "status" in node:
                    the_node.extra_attributes["status"]=node["status"]
            if len(nodes)>0:
                log.notice("nodes %d" % len(nodes))
            return 
        except:
            log.exception("can't parse pbsnodes output: %s"%pbsnodes_output)
            return 

    def query_jobs(self):
        self.state["torque"], qstat_output=torque_utils.job_query(self.config['qstat_command'])
        self.state["maui"], diag_p_output=torque_utils.job_query(self.config['diagnose_p_command'])
        if self.state["torque"]==False or self.state["maui"]==False:
            return
        if len(qstat_output)==0:
            log.notice("There is no job in the queue.")
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
        log.notice("jobs: %s" % raw_queued_jobs)
        try:
            lines=diag_p_output.split("\n")
            for each_line in lines[5:]:
                if not each_line.strip():
                    break
                #log.notice("each_line %s"%each_line)
                items=each_line.split()
                #log.notice("items %s"%items)
                job_id=items[0].strip()
                if job_id not in raw_queued_jobs:
                    continue
                job_dict=raw_queued_jobs[job_id]
                job=Job(job_id)
                job.name=job_dict["Job_Name"]
                job.owner=job_dict["Job_Owner"]
                if "queue" in job_dict:
                    job.queue=job_dict["queue"]
                if "Resource_List.walltime" in job_dict:
                    job.requested_walltime=job_dict["Resource_List.walltime"]
                if "Resource_List.mem" in job_dict:
                    job.requested_mem=job_dict["Resource_List.mem"]
                if "Resource_List.nodes" in job_dict:
                    strs=job_dict["Resource_List.nodes"].split(":")
                    num_cores=1
                    num_nodes=1
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
                            job.property=strs[1]
                    if len(strs)>2:
                        job.property=strs[2]
                    job.requested_cores=num_nodes*num_cores
                    job.cores_per_node=num_cores
                elif "Resource_List.ncpus" in job_dict:
                    job.cores_per_node=int(job_dict["Resource_List.ncpus"])
                #elif "Resource_List.nodes" not in job_dict and "Resource_List.ncpus" not in job_dict:
                #    job.requested_proc=ProcRequirement()
                if "Account_Name" in job_dict:
                    job.account=job_dict["Account_Name"]
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
            
    def on_instance_ready(self, worker_node, reservation):
        log.debug("workernode %s is ready, add it to cluster"%worker_node.hostname)
        if self.add_node(worker_node, reservation):
            # run post add_node_command here!
            if "post_add_node_command" in self.config:
                run_post_command(worker_node, self.config["post_add_node_command"])
        else:
            log.debug("cannot add node %s to cluster, delete it"%worker_node.hostname)
            self.remove_node(worker_node, reservation)
            if "post_remove_node_command" in self.config:
                run_post_command(worker_node, self.config["post_remove_node_command"])
            worker_node.state=WorkerNode.Deleting
            worker_node.state_start_time=time.time()
            
    def check_reservation(self, wn, reservation):
        if "queue" in reservation and reservation['queue'] is not None:
            current_res=torque_utils.show_res_of_node(wn, self.config['showres_command'])
            need_fix=True
            if current_res is not None:
                res_line=[l for l in current_res.split('\n') if reservation['queue']+'.' in l]
                if len(res_line)>0:
                    need_fix=False
            if need_fix:
                log.debug("node %s is not reserved for queue %s, fix it now"%(wn.hostname,reservation['queue'] ))
                torque_utils.set_res_for_node(wn, "queue", reservation['queue'], self.config['setres_command'])
        if "account" in reservation and reservation['account'] is not None:
            current_res=torque_utils.show_res_of_node(wn, self.config['showres_command'])
            need_fix=True
            if current_res is not None:
                res_line=[l for l in current_res.split('\n') if reservation['account']+'.' in l]
                if len(res_line)>0:
                    need_fix=False
            if need_fix:
                log.debug("node %s is not reserved for account %s, fix it now"%(wn.hostname,reservation['account'] ))
                torque_utils.set_res_for_node(wn, "account", reservation['account'], self.config['setres_command'])
        if "property" in reservation and reservation['property'] is not None:
            if 'properties' not in wn.extra_attributes or reservation['property'] not in wn.extra_attributes['properties']:
                log.debug("node %s is not reserved for property %s, fix it now"%(wn.hostname,reservation['property'] ))
                torque_utils.set_node_property(wn, reservation['property'], self.config['set_node_command'])
        
    def add_node(self, wn, reservation):
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
        torque_utils.set_np(wn, self.config['set_node_command'])
        #time.sleep(2)
        #check if the new VM is added to torque
        retry=60
        while retry>0:
            node_state, s = torque_utils.check_node(wn, self.config['check_node_command'])
            if node_state is not None and node_state!='gone':
                break
            retry-=1
            log.debug("vm %s is not showing in maui yet" % wn.hostname)
            time.sleep(1)
        if node_state is None:
            log.error("cannot see %s in maui, delete it" % wn.hostname)
            torque_utils.remove_node_from_torque(wn, self.config['remove_node_command'])
            return False
        # set account string to wn
        if "queue" in reservation and reservation['queue'] is not None:
            retry=5
            while retry>0:
                if torque_utils.set_res_for_node(wn, "queue", reservation['queue'], self.config['setres_command'])==True:
                    break
                retry-=1
            if retry==0:
                log.error("cannot set reservation for %s, delete it"% wn.hostname)
                return False
        if "account" in reservation and reservation['account'] is not None:
            retry=5
            while retry>0:
                if torque_utils.set_res_for_node(wn, "account", reservation['account'], self.config['setres_command'])==True:
                    break
                retry-=1
            if retry==0:
                log.error("cannot set reservation for %s, delete it"% wn.hostname)
                return False
        if "property" in reservation and reservation['property'] is not None:
            torque_utils.set_node_property(wn, reservation['property'], self.config['set_node_command'])
            time.sleep(2)
        # this is not needed for Torque 5.1.1
        torque_utils.set_node_online(wn, self.config['set_node_command'])
        time.sleep(2)
        return True
    
    def remove_node(self, wn, reservation):
        log.debug("removing node %s from cluster" % wn)
        if "queue" in reservation and reservation['queue'] is not None:
            torque_utils.release_res_for_node(wn, reservation['queue'], self.config['releaseres_command'])
        if "account" in reservation and reservation['account'] is not None:
            torque_utils.release_res_for_node(wn, reservation['account'], self.config['releaseres_command'])
        torque_utils.hold_node_in_torque(wn, self.config['pbsnodes_command'])
        #check if the VM is drained in MAUI
        retry=60
        while retry>0:
            node_state, s = torque_utils.check_node(wn, self.config['check_node_command'])
            if node_state in ["drained", "down", "gone"]:
                break
            retry-=1
            log.debug("state of wn %s is not populated to maui yet" % wn.hostname)
            time.sleep(1)
        if node_state not in ["drained", "down", "gone"]:
            log.error("cannot see updated state of %s in maui, try again later" % wn.hostname)
            return False
        torque_utils.remove_node_from_torque(wn, self.config['remove_node_command'])
        return True
    
    def hold_node(self, wn):
        log.debug("hold node %s in cluster" % wn)
        torque_utils.hold_node_in_torque(wn, self.config['pbsnodes_command'])
        
    def unhold_node(self, wn):
        log.debug("unhold node %s in cluster" % wn)
        torque_utils.set_node_online(wn, self.config['set_node_command'])

    def vacate_node(self, wn):
        if wn.jobs is None:
            return
        log.debug("jobs %s" % wn.jobs)
        for jobid in wn.jobs.split(", "):
            if "/" in jobid:
                jobid=jobid.split('/')[1]
            log.debug("killing job %s" % jobid)
            torque_utils.signal_job(jobid, "9", self.config['signal_job_command'])
            torque_utils.delete_job(jobid, self.config['delete_job_command'])

class SGEManager(ClusterManager):
    def __init__(self, config):
        ClusterManager.__init__(self, config, {"sge":True})

    def update_worker_nodes(self, worker_node_list):
        self.state["sge"], qhost_output=sge_utils.wn_query(self.config['qhost_command'])
        try:
            root = ET.fromstring(qhost_output)
            for raw_node in root.findall('host'):
                if raw_node.get("name")=="global":
                    continue
                node = {"name":raw_node.get("name"), "jobs":[]}
                for child in raw_node:
                    if child.tag == "hostvalue":
                        node[child.get("name")]=child.text
                    elif child.tag == "job":
                        node["jobs"].append(child.get("name"))
                    elif child.tag == "queue":
                        for grand_child in child:
                            node['queue.'+grand_child.get("name")]=grand_child.text
                #if not config.node_property or ('properties' in node and node['properties'].find(config.node_property)>-1):
                #print worker_node_list
                log.notice("node %s" % node)
                nodes=[n for n in worker_node_list if n.hostname==node["name"]]
                the_node=None
                if len(nodes)>0:
                    the_node=nodes[0]
                else:
                    the_node=WorkerNode(node["name"])
                    the_node.state_start_time=time.time()
                    if node["num_proc"].isdigit():
                        the_node.num_proc=int(node["num_proc"])
                    worker_node_list.append(the_node)
                if len(node["jobs"])>0:
                    the_node.jobs=node["jobs"]
                else:
                    the_node.jobs=None
                if "queue.state_string" in node and node["queue.state_string"] is not None:
                    if "d" in node["queue.state_string"]:
                        if the_node.state!=WorkerNode.Held:
                            the_node.state_start_time=time.time()
                        the_node.state=WorkerNode.Held
                    if "E" in node["queue.state_string"] or ("u" in node["queue.state_string"] and the_node.state!=WorkerNode.Starting):
                        if the_node.state!=WorkerNode.Error:
                            the_node.state_start_time=time.time()
                        the_node.state=WorkerNode.Error
                else:
                    if the_node.jobs is None:
                        if the_node.state!=WorkerNode.Idle:
                            the_node.state_start_time=time.time()
                        the_node.state=WorkerNode.Idle
                    else:
                        if the_node.state!=WorkerNode.Busy:
                            the_node.state_start_time=time.time()
                        the_node.state=WorkerNode.Busy
                the_node.extra_attributes={"arch_string": node["arch_string"], 
                                             "m_socket": node["m_socket"],
                                             "load_avg": node["load_avg"],
                                             "mem_total": node["mem_total"],
                                             "mem_used": node["mem_used"],
                                             "swap_total": node["swap_total"],
                                             "swap_used": node["swap_used"],
                                             "m_core": node["m_core"], "m_thread": node["m_thread"]
                                             }
            if len(nodes)>0:
                log.notice("nodes %d" % len(nodes))
            return 
        except:
            log.exception("can't parse qhost output: %s"%qhost_output)
            return 

    def query_jobs(self):
        self.state["sge"], qstat_output=sge_utils.job_query(self.config['qstat_command'])
        log.notice("qstat output %s" % qstat_output)
        pe_names=sge_utils.get_pes(self.config['qconf_spl_command'])
        if len(pe_names)>0:
            pes={}
            for pe in pe_names.split('\n'):
                pes[pe]=sge_utils.get_pe_allocation_rule(self.config['qconf_sp_command'], pe)
            log.notice("pes %s" % pes)
        try:
            queued_jobs = []
            running_jobs = []
            num_of_jobs = 0
            total_number_of_idle_jobs = 0
    
            root = ET.fromstring(qstat_output)
            raw_queued_jobs={}
            for raw_job in root.findall('job_info/job_list'):
                job = {"job_state": raw_job.get("state")}
                for child in raw_job:
                    log.notice("child %s" % child)
                    if child.tag=="requested_pe":
                        job["requested_pe.name"]=child.get("name")
                        job["requested_pe"]=child.text
                    elif "name" in child.attrib:
                        job[child.tag+"."+child.get("name")]=child.text
                    else:
                        job[child.tag]=child.text
                job_id=job["JB_job_number"]
                log.notice("raw_job %s" % job)
                if job['job_state']=="pending": # and (len(self.config['queue_to_monitor'])==0 or job['queue'] in self.config['queue_to_monitor']):
                    total_number_of_idle_jobs+=1
                    if self.config['queued_job_number_to_display'] < 1 or (self.config['queued_job_number_to_display'] > 0 and num_of_jobs<self.config['queued_job_number_to_display']):
                        new_job=Job(job_id)
                        new_job.name=job["JB_name"]
                        new_job.owner=job["JB_owner"]
                        if "hard_req_queue" in job:
                            new_job.queue=job["hard_req_queue"]
                        if float(job["JAT_prio"])>0:
                            new_job.priority=float(job["JAT_prio"])
                        if "hard_request.h_rt" in job:
                            new_job.requested_walltime=job["hard_request.h_rt"]
                        if "hard_request.mem_free" in job:
                            new_job.requested_mem=job["hard_request.mem_free"]
                        if "requested_pe" in job:
                            new_job.requested_cores=int(job["requested_pe"])
                            if pes[job["requested_pe.name"]] in ["$round_robin", "$fill_up"]:
                                new_job.cores_per_node=0
                            elif pes[job["requested_pe.name"]] == "$pe_slots":
                                new_job.cores_per_node=new_job.requested_cores
                            elif pes[job["requested_pe.name"]].isdigit():
                                new_job.cores_per_node=int(pes[job["requested_pe.name"]])
                        new_job.state=Job.Queued
                        new_job.creation_time=unix_time(datetime.datetime.strptime(job['JB_submission_time'], "%Y-%m-%dT%H:%M:%S"))
                        queued_jobs.append(new_job)
                        num_of_jobs=+1
                elif job['job_state']=="running":
                    new_job=Job(job_id)
                    new_job.priority=float(job["JAT_prio"])
                    new_job.state=Job.Running
                    running_jobs.append(new_job)
            log.notice("queued_jobs %s" % queued_jobs)
            return queued_jobs, total_number_of_idle_jobs
        except:
            log.exception("cannot parse qstat output: %s" % qstat_output)
            return [], 0
    
    def on_instance_active(self, worker_node, reservation):
        log.debug("workernode %s is provisioned, add it to cluster"%worker_node.hostname)
        if self.add_node(worker_node, reservation):
            #workernodes[0].state=WorkerNode.Idle
            #workernodes[0].state_start_time=time.time()
            # run post add_node_command here!
            if "post_add_node_command" in self.config:
                run_post_command(worker_node, self.config["post_add_node_command"])
        else:
            log.debug("cannot add node %s to cluster, delete it"%worker_node.hostname)
            self.remove_node(worker_node, reservation)
            if "post_remove_node_command" in self.config:
                run_post_command(worker_node, self.config["post_remove_node_command"])
            worker_node.state=WorkerNode.Deleting
            worker_node.state_start_time=time.time()

    def on_instance_ready(self, worker_node, reservation):
        log.info("workernode %s is ready now."%worker_node.hostname)
        worker_node.state=WorkerNode.Idle
        worker_node.state_start_time=time.time()
    
    def check_reservation(self, wn, reservation):
        return
    
    def add_node(self, wn, reservation):
        if sge_utils.update_hostgroup(wn, self.config['hostgroup_command'], "-aattr", reservation['account']):
            return sge_utils.set_slots(wn, self.config['set_slots_command'], reservation['queue'])
        return False
        
    def hold_node(self, wn):
        log.debug("hold node %s in cluster" % wn)
        sge_utils.disable_node_in_sge(wn, self.config['qmod_command'])

    def unhold_node(self, wn):
        log.debug("unhold node %s in cluster" % wn)
        torque_utils.enable_node_in_sge(wn, self.config['set_node_command'])

    def remove_node(self, wn, reservation):
        log.debug("removing node %s from cluster" % wn)
        if wn.jobs:
            return False
#             for j in jobs:
#                 log.debug("deleting job %s"%j)
#                 sge_utils.delete_job(j)
        sge_utils.update_hostgroup(wn, self.config['hostgroup_command'], "-dattr", reservation['account'])
        time.sleep(.5)
        sge_utils.unset_slots(wn, self.config['unset_slots_command'], reservation['queue'])
        time.sleep(.5)
        return sge_utils.remove_node_from_sge(wn, self.config['remove_node_command'])

    def vacate_node(self, wn):
        if wn.jobs is None:
            return
        for j in jobs:
            log.debug("deleting job %s"%j)
            sge_utils.delete_job(j)
