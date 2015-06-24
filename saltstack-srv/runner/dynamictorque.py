# -*- coding: utf-8 -*-

from __future__ import absolute_import

import salt.pillar
import salt.wheel
from subprocess import Popen, PIPE

def process_minion_request(minion_id):
    saltenv = 'base'
    id_, grains, _ = salt.utils.minions.get_minion_data("*", __opts__)
    if grains is None:
        grains = {'fqdn': "*"}

    pillar = salt.pillar.Pillar(
        __opts__,
        grains,
        id_,
        saltenv)

    compiled_pillar = pillar.compile_pillar()

    try:
        process = Popen(shlex.split(compiled_pillar["get_starting_instance_names_cmd"]), stdout=PIPE)
        pipe = process.stdout
        output = pipe.readlines()
        process.wait()
        returncode = process.returncode
    except:
        print "Dynamic Torque is not running."
        return False
    else:
        wheel = salt.wheel.Wheel(__opts__)
        if minion_id in output:
            wheel.call_func('key.accept', match=minion_id)
        else:
            wheel.call_func('key.reject', match=minion_id)
        return True