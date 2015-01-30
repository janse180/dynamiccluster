import subprocess
import string
import shlex
import re

from dynamiccluster.utilities import getLogger

log = getLogger(__name__)

def wn_query(qhost_command):
    """ query worker nodes """
    log.notice("Querying SGE with %s" % qhost_command.format("", ""))
    qhost = shlex.split(qhost_command.format("", ""))
    try:
        sp = subprocess.Popen(qhost, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (query_out, query_err) = sp.communicate(input=None)
        returncode = sp.returncode
    except:
        log.exception("Problem running %s, unexpected error" % string.join(qhost, " "))
        return False, []

    if returncode != 0:
        if "No nodes found" not in query_err:
            log.error("Got non-zero return code '%s' from '%s'. stderr was: %s" %
                          (returncode, string.join(qhost, " "), query_err))
            sge_up = False
        else:
            sge_up = True
        return sge_up, ""

    return True, query_out

def job_query(qstat_command):
    """job_query_local -- query and parse condor_q for job information."""
    log.notice("Querying SGE with %s" % qstat_command)
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

def update_hostgroup(wn, hostgroup_command, option, group_name):
    log.debug("update hostgroup %s for %s with option %s" % (group_name, wn.hostname, option))
    cmd=hostgroup_command.format(option, wn.hostname, group_name)
    log.notice("cmd %s"%cmd)
    try:
        add_node = shlex.split(cmd)
        sp = subprocess.Popen(add_node, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
#           log.verbose("%s: %s %s"%(string.join(add_node, " ")%cmd_out%cmd_err))
        if returncode != 0:
            log.error("Error updating hostgroup %s for %s with option %s in sge, returncode %s"% (group_name, wn.hostname, option, returncode))
            log.debug("cmd_out %s cmd_err %s" % (cmd_out,cmd_err))
            return False
        return True
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return False

def hold_node_in_sge(wn, qmod_command):
    log.debug("disabling all queues in node %s" % (wn.hostname))
    cmd=qmod_command.format("-d", wn.hostname)
    try:
        hold_node = shlex.split(cmd)
        sp = subprocess.Popen(hold_node, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
        if returncode != 0:
            log.error("Error when disabling node %s in sge, returncode %s"% (wn.hostname, returncode))
            log.debug("cmd_out %s cmd_err %s" % (cmd_out,cmd_err))
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return 

def remove_node_from_sge(wn, remove_node_command):
    log.debug("removing node %s from sge" % (wn.hostname))
    try:
        remove_node = shlex.split(remove_node_command.format(wn.hostname))
        sp = subprocess.Popen(remove_node, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
        if returncode != 0:
            log.error("Error when removing %s from sge, returncode %s"% (wn.hostname, returncode))
            log.debug("cmd_out %s cmd_err %s" % (cmd_out,cmd_err))
    except:
        log.exception("Problem running %s, unexpected error" % string.join(remove_node, " "))
        return 

def set_slots(wn, set_slots_command, queue):
    log.debug("setting slots for %s@%s" % (queue, wn.hostname))
    try:
        cmd = shlex.split(set_slots_command.format(wn.num_proc, queue, wn.hostname))
        sp = subprocess.Popen(cmd, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
        if returncode != 0:
            log.error("Error when setting slots for %s@%s, returncode %s"% (queue, wn.hostname, returncode))
            log.debug("cmd_out %s cmd_err %s" % (cmd_out,cmd_err))
    except:
        log.exception("Problem running %s, unexpected error" % string.join(cmd, " "))
        return 

def unset_slots(wn, unset_slots_command, queue):
    log.debug("unsetting slots for %s@%s" % (queue, wn.hostname))
    try:
        cmd = shlex.split(unset_slots_command.format(queue, wn.hostname))
        sp = subprocess.Popen(cmd, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
        if returncode != 0:
            log.error("Error when unsetting slots for %s@%s, returncode %s"% (queue, wn.hostname, returncode))
            log.debug("cmd_out %s cmd_err %s" % (cmd_out,cmd_err))
    except:
        log.exception("Problem running %s, unexpected error" % string.join(cmd, " "))
        return 
    