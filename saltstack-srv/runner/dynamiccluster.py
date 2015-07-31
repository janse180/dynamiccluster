# -*- coding: utf-8 -*-

from __future__ import absolute_import

import salt.pillar
import salt.wheel
import requests

import logging
log = logging.getLogger(__name__)

def process_minion_request(minion_id, url="http://localhost:8001/workernode?state=1"):
    try:
        r = requests.get(url)
    except:
        log.error("Error when connecting to Dynamic Cluster.")
        return False
    else:
        wns=r.json()
        log.debug("wns %s" % wns)
        starting_ids=[wn['instance']['instance_name'] for wn in wns]
        wheel = salt.wheel.Wheel(__opts__)
        if minion_id in starting_ids:
            wheel.call_func('key.accept', match=minion_id)
        else:
            wheel.call_func('key.reject', match=minion_id)
        return True