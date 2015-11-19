from dynamiccluster.utilities import getLogger

import string, shlex, subprocess

log = getLogger(__name__)

def run_post_command(wn, command):
    cmd=command.format(wn.hostname, wn.instance.ip, wn.instance.instance_name, wn.instance.cloud_resource)
    log.info("post command (%s): %s"%(wn.hostname,cmd))
    try:
        post_action = shlex.split(cmd)
        sp = subprocess.Popen(post_action, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
        if returncode != 0:
            log.error("Error running post script for %s"%wn.hostname)
            log.debug("cmd_out %s cmd_err %s"%(cmd_out, cmd_err))
    except:
        log.exception("Problem running %s, unexpected error" % cmd)
        return 

