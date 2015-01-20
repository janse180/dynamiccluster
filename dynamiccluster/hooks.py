from dynamiccluster.utilities import getLogger

log = getLogger(__name__)

def run_post_vm_provision_command(wn, command):
    cmd=command.format(wn.hostname, wn.instance.ip, wn.instance.instance_name)
    log.debug("post vm-provision command (%s): %s"%(wn.hostname,cmd))
    try:
        post_action = shlex.split(cmd)
        sp = subprocess.Popen(post_action, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
        if returncode != 0:
            log.debug("cmd_out %s cmd_err %s"%(cmd_out, cmd_err))
            log.error("Error running post-vm-provision script for %s"%wn.hostname)
    except:
        log.exception("Problem running %s, unexpected error" % string.join(post_action, " "))
        return 

def post_config_node_command(wn, command):
    cmd=command.format(wn.hostname, wn.instance.ip)
    log.debug("post config-node command (%s): %s"%(wn.hostname,cmd))
    try:
        post_action = shlex.split(cmd)
        sp = subprocess.Popen(post_action, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
        if returncode != 0:
            log.debug("cmd_out %s cmd_err %s"%(cmd_out, cmd_err))
            log.error("Error running post-add-node script for %s"%wn.hostname)
    except:
        log.exception("Problem running %s, unexpected error" % string.join(post_action, " "))
        return 

def post_remove_node_action(vm):
    if not config.post_remove_node_command:
        return
    cmd=config.post_remove_node_command.format(vm.hostname, vm.ip)
    log.debug("post remove-node action (%s): %s"%(vm.hostname,cmd))
    try:
        post_action = shlex.split(cmd)
        sp = subprocess.Popen(post_action, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
        if returncode != 0:
            log.error("Error running post-remove-node script for %s"%vm.hostname)
            log.debug("cmd_out %s cmd_err %s"%(cmd_out, cmd_err))
    except:
        log.exception("Problem running %s, unexpected error" % string.join(post_action, " "))
        return 

def post_vm_destroy_action(vm):
    if not config.post_vm_destroy_command:
        return
    cmd=config.post_vm_destroy_command.format(vm.hostname, vm.ip, vm.name)
    log.debug("post vm-destroy action (%s): %s"%(vm.hostname,cmd))
    try:
        post_action = shlex.split(cmd)
        sp = subprocess.Popen(post_action, shell=False,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (cmd_out, cmd_err) = sp.communicate(input=None)
        returncode = sp.returncode
        if returncode != 0:
            log.error("Error running post-vm-destroy script for %s"%vm.hostname)
            log.debug("cmd_out %s cmd_err %s"%(cmd_out, cmd_err))
    except:
        log.exception("Problem running %s, unexpected error" % string.join(post_action, " "))
        return 
