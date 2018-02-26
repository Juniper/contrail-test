"""Module to hold the test case related utilites.
"""
import platform

from fabric.api import local

def get_release(pkg='contrail-install-packages'):
    pkg_ver = None
    dist = platform.dist()[0]
    if dist in ['centos', 'fedora', 'redhat']:
        cmd = "rpm -q --queryformat '%%{VERSION}' %s" %pkg
    elif dist in ['Ubuntu']:
        cmd = "dpkg -p %s | grep Version: | cut -d' ' -f2 | cut -d'-' -f1" %pkg
    pkg_ver = local(cmd, capture=True)
    if 'is not installed' in pkg_ver or 'is not available' in pkg_ver:
        print "Package %s not installed." % pkg
        return None
    return pkg_ver
