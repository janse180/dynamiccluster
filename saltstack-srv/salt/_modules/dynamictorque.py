# -*- coding: utf-8 -*-

def get_starting_instance_names(cmd):
    process = Popen(shlex.split(cmd), stdout=PIPE)
    pipe = process.stdout
    output = pipe.readlines()
    process.wait()
    return output
