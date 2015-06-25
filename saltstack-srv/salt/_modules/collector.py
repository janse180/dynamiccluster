# -*- coding: utf-8 -*-

import time

def _readfile(filename):
    with open(filename) as f:
        content = f.readlines()
    return content

def collect_load_avg():
    data=_readfile("/proc/loadavg")
    variables=data[0].split(" ")
    return {"tag": "loadavg", "timestamp": int(time.time()), "1m": variables[0], "5m": variables[1], "15m": variables[2]}