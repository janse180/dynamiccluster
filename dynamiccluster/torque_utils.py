import subprocess
import string
import shlex
import re

from dynamiccluster.utilities import getLogger

log = getLogger(__name__)

def wn_query(pbsnodes_command):
    """ query worker nodes """
    log.notice("Querying Torque with %s" % pbsnodes_command.format("-x", ""))
    pbsnodes = shlex.split(pbsnodes_command.format("-x", ""))
    try:
        sp = subprocess.Popen(pbsnodes, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (query_out, query_err) = sp.communicate(input=None)
        returncode = sp.returncode
    except:
        log.exception("Problem running %s, unexpected error" % string.join(pbsnodes, " "))
        return False, []

    if returncode != 0:
        if "No nodes found" not in query_err:
            log.error("Got non-zero return code '%s' from '%s'. stderr was: %s" %
                          (returncode, string.join(pbsnodes, " "), query_err))
            pbs_server_up = False
        else:
            pbs_server_up = True
        return pbs_server_up, ""

    return True, query_out

def job_query(qstat_command):
    """job_query_local -- query and parse condor_q for job information."""
    log.notice("Querying Torque with %s" % qstat_command)
    qstat = shlex.split(qstat_command)
    try:
        sp = subprocess.Popen(qstat, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (query_out, query_err) = sp.communicate(input=None)
        returncode = sp.returncode
    except:
        log.exception("Problem running %s, unexpected error" % string.join(qstat, " "))
        return False, ""

    if returncode != 0:
        log.error("Got non-zero return code '%s' from '%s'. stderr was: %s" %
                          (returncode, string.join(qstat, " "), query_err))
        return False, ""

    if query_out.strip()=="":
        return True, ""
    return True, query_out

def get_job_priorities(diagnose_p_command):
    """ give each job a priority """
    log.notice("Querying Maui with %s" % diagnose_p_command)
    try:
        diagnose = shlex.split(diagnose_p_command)
        sp = subprocess.Popen(diagnose, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (query_out, query_err) = sp.communicate(input=None)
        returncode = sp.returncode
    except:
        log.exception("Problem running %s, unexpected error" % string.join(diagnose, " "))
        return False, ""

    if returncode != 0:
        log.error("Got non-zero return code '%s' from '%s'. stderr was: %s" %
                          (returncode, string.join(diagnose, " "), query_err))
        return False, "" 
    return True, query_out

def add_node_to_torque(wn, add_node_command):
    log.debug("adding %s to torque"%wn.hostname)
    cmd=add_node_command.format(wn.hostname)
    log.notice("cmd %s"%cmd)
    try:
        add_node = shlex.split(cmd)
        sp = subprocess.Popen(add_node, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.error("Error adding node %s to torque, returncode %s"% (wn.hostname, returncode))
            log.debug("cmd_out %s cmd_err %s" % (cmd_out,cmd_err))
            return False
        return True
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return False

def check_node(wn, check_node_command):
    try:
        maui_check_node = shlex.split(check_node_command.format(wn.hostname))
        sp = subprocess.Popen(maui_check_node, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
        if returncode == 1 and "cannot locate node" in cmd_err:
            log.error("node %s doesn't exist in maui." % wn.hostname)
            return "gone", 0
        if returncode != 0:
            log.error("checknode returns error, probably the node does not exist. returncode %s" % returncode)
            log.debug("cmd_out %s cmd_err %s" % (cmd_out,cmd_err))
            return None, 0
        m=re.search("(.*)State:(.*)\(in current state for (.*)\)(.*)",cmd_out,re.M|re.I)
        if m is not None and len(m.groups())>3:
            state=m.groups()[1].strip().lower()
            length=m.groups()[2].strip()
            log.notice("wn %s is in current state %s for %s"%(wn.hostname, state, length))
            numbers=list(reversed(length.split(":")))
            total_seconds=int(numbers[0])
            if len(numbers)>1:
                total_seconds+=int(numbers[1])*60
            if len(numbers)>2:
                total_seconds+=int(numbers[2])*3600
            if len(numbers)>3:
                total_seconds+=int(numbers[3])*86400
            return state, total_seconds
        else:
            log.error("can't find node's state from")
            log.error("cmd_out %s" % cmd_out)
            log.error("cmd_err %s" % cmd_err)
            log.error("returncode %s" % returncode)
            log.debug("m %s" % m)
    except:
        log.exception("Problem running %s, unexpected error" % string.join(maui_check_node, " "))
        return None, 0

def remove_node_from_torque(wn, remove_node_command):
    try:
        remove_node = shlex.split(remove_node_command.format(wn.hostname))
        sp = subprocess.Popen(remove_node, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
    except:
        log.exception("Problem running %s, unexpected error" % string.join(remove_node, " "))
        return 

def set_np(wn, set_node_command):
    log.debug("setting np=%s to node %s"%(wn.instance.vcpu_number, wn.hostname))
    cmd=set_node_command.format(wn.hostname,"np","=",str(wn.instance.vcpu_number))
    log.notice("cmd %s"%cmd)
    try:
        set_np = shlex.split(cmd)
        sp = subprocess.Popen(set_np, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.error("Error setting np to node %s"%wn.hostname)
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return 

def set_node_property(wn, node_property, set_node_command):
    log.debug("setting %s to node %s"%(node_property,wn.hostname))
    cmd=set_node_command.format(wn.hostname,"properties","=",node_property)
    log.notice("cmd %s"%cmd)
    try:
        set_node_property = shlex.split(cmd)
        sp = subprocess.Popen(set_node_property, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.error("Error setting property to node %s"%wn.hostname)
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return 

def hold_node_in_torque(wn, pbsnodes_command):
    cmd=pbsnodes_command.format("-o", wn.hostname)
    try:
        hold_node = shlex.split(cmd)
        sp = subprocess.Popen(hold_node, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return 

def add_node_property(wn, node_property, set_node_command):
    log.debug("adding %s to node %s"%(node_property,wn.hostname))
    cmd=set_node_command.format(wn.hostname,"properties","+=",node_property)
    log.notice("cmd %s"%cmd)
    try:
        add_node_property = shlex.split(cmd)
        sp = subprocess.Popen(add_node_property, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.error("Error adding property to node %s"%wn.hostname)
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return 

def set_node_online(wn, set_node_command):
    log.debug("setting node %s online"%(wn.hostname))
    try:
        set_node_online = shlex.split(set_node_command.format(wn.hostname,"state","=","free"))
        sp = subprocess.Popen(set_node_online, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.error("Error setting node %s online: %s; %s"%(wn.hostname,cmd_out, cmd_err))
    except:
        log.exception("Problem running set_node_command %s, unexpected error"%wn.hostname)
        return

def show_res_of_node(wn, showres_command):
    log.debug("getting reservations of node %s"%wn.hostname)
    cmd=showres_command.format(wn.hostname)
    log.debug("cmd %s"%cmd)
    try:
        sp = subprocess.Popen(cmd, shell=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.debug("can't find reservation for node %s, return code %s"%(wn.hostname, returncode))
            log.debug("cmd_out %s cmd_err %s"%(cmd_out, cmd_err))
            return None
        return cmd_out
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return None

def set_res_for_node(wn, res_type, res_name, setres_command):
    log.debug("setting reservation (type=%s) for node %s"%(res_type, wn.hostname))
    res_opt={"account":"-a","queue":"-q"}.get(res_type)
    if res_opt is None:
        log.error("res_type %s is not supported"%res_type)
        return
    cmd=setres_command.format(res_opt,res_name,wn.hostname)
    log.debug("cmd %s"%cmd)
    try:
        set_res = shlex.split(cmd)
        sp = subprocess.Popen(set_res, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.error("Error reservation for node %s, return code %s"%(wn.hostname, returncode))
            log.debug("cmd_out %s cmd_err %s"%(cmd_out, cmd_err))
            return False
        return True
    except:
        log.exception("Problem running %s, unexpected error" % string.join(set_res, " "))
        return False

def release_res_for_node(wn, res_name, releaseres_command):
    log.debug("releasing reservation %s for node %s"%(res_name, wn.hostname))
    release_node = releaseres_command.format(wn.hostname, res_name)
    log.debug("cmd %s"%release_node)
    try:
        sp = subprocess.Popen(release_node, shell=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.error("Error releasing reservation for node %s, return code %s"%(wn.hostname, returncode))
            log.debug("cmd_out %s cmd_err %s"%(cmd_out, cmd_err))
    except:
        log.exception("Problem running %s, unexpected error" % release_node)
        return

def delete_job(jobid, del_job_command):
    log.debug("deleting job %s"%jobid)
    del_job = del_job_command.format(jobid)
    log.debug("cmd %s"%del_job)
    try:
        sp = subprocess.Popen(del_job, shell=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.error("Error deleting job %s, return code %s"%(jobid, returncode))
            log.debug("cmd_out %s cmd_err %s"%(cmd_out, cmd_err))
    except:
        log.exception("Problem running %s, unexpected error" % del_job)
        return

def signal_job(jobid, signal, signal_job_command):
    log.debug("sending signal %s to job %s"%(signal,jobid))
    qsig_job = signal_job_command.format(signal, jobid)
    log.debug("cmd %s"%qsig_job)
    try:
        sp = subprocess.Popen(qsig_job, shell=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.error("Error sending signal %s to job %s, return code %s"%(signal, jobid, returncode))
            log.debug("cmd_out %s cmd_err %s"%(cmd_out, cmd_err))
    except:
        log.exception("Problem running %s, unexpected error" % qsig_job)
        return
    