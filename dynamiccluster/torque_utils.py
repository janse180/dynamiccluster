import subprocess

from dynamiccluster.utilities import getLogger

log = getLogger(__name__)


def wn_query(pbsnodes_command):
    """ query worker nodes """
    log.notice("Querying Torque with %s" % pbsnodes_command.format("-x", ""))
    try:
        pbsnodes = shlex.split(pbsnodes_command.format("-x", ""))
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
    try:
        qstat = shlex.split(config.qstat_command)
        sp = subprocess.Popen(qstat, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (query_out, query_err) = sp.communicate(input=None)
        returncode = sp.returncode
    except:
        log.exception("Problem running %s, unexpected error" % string.join(qstat, " "))
        return False, 0, [], []

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
