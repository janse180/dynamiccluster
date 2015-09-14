#! /bin/env python

import sys
import os
import tarfile
import argparse
from os.path import dirname, join, abspath
from shutil import copy, copytree, rmtree
from subprocess import check_call
from contextlib import closing

parser = argparse.ArgumentParser(
        description='Build dynamic cluster rpms',
        )
parser.add_argument('buildid',
        help='The build id to use i.e. the bit after the salt version in the package name',
        )
args = parser.parse_args()

src = abspath(join(dirname(__file__), '..'))

sys.path.append(src)

from dynamiccluster.__version__ import version

rpmbuild = join(os.environ['HOME'], 'rpmbuild')
if os.path.exists(join(rpmbuild, 'SOURCES')):
    rmtree(join(rpmbuild, 'SOURCES'))
copy(join(src, 'pkg/rpm.spec'), join(rpmbuild, 'SPECS'))
os.makedirs(join(rpmbuild, 'SOURCES'))
copy(join(src, 'scripts/initd-script'), join(rpmbuild, 'SOURCES'))
copy(join(src, 'config/dynamiccluster.yaml'), join(rpmbuild, 'SOURCES'))
#copytree(src, join(rpmbuild, 'SOURCES'))
# for f in os.listdir(src):
#     if f in ['bin', 'pkg', 'tests', 'README.md', 'test.sh']:
#         continue
#     print('copying %s...'%f)
#     if os.path.isdir(join(src, f)):
#         copytree(join(src, f), join(rpmbuild, 'SOURCES'))
#     else:
#         copy(join(src, f), join(rpmbuild, 'SOURCES'))


def srcfilter(ti):
    if '/.git' in ti.name:
        return None
    return ti

with closing(tarfile.open(join(rpmbuild, 'SOURCES/dynamiccluster-%s.tar.gz' % version), 'w|gz')) as tf:
    tf.add(src, arcname='dynamiccluster-%s' % version)


cmd = ['rpmbuild', '-bb',
       '--define=version %s' % version,
       '--define=buildid %s' % args.buildid,
       'rpm.spec']
print('Executing: %s' % ' '.join('"%s"' % c for c in cmd))
check_call(cmd, cwd=join(rpmbuild, 'SPECS'))