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

def add_node_to_sge(wn, add_node_command):
    log.debug("adding %s to sge"%wn.hostname)
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
            log.error("Error adding node %s to sge, returncode %s"% (wn.hostname, returncode))
            log.debug("cmd_out %s cmd_err %s" % (cmd_out,cmd_err))
            return False
        return True
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return False

def hold_node_in_sge(wn, qmod_command):
    cmd=qmod_command.format("-d", wn.hostname)
    try:
        hold_node = shlex.split(cmd)
        sp = subprocess.Popen(hold_node, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return 

def remove_node_from_sge(wn, remove_node_command):
    try:
        remove_node = shlex.split(remove_node_command.format(wn.hostname))
        sp = subprocess.Popen(remove_node, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
    except:
        log.exception("Problem running %s, unexpected error" % string.join(remove_node, " "))
        return 
