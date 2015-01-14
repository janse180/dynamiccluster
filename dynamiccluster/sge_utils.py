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
