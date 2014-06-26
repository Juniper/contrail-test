import tempfile
import sys
import string
import ConfigParser
import argparse
import socket
import json
from netaddr import *
import re
import xml.etree.ElementTree as ET
import os
import subprocess
import time

CONTRAIL_FEDORA_TEMPL = string.Template("""
[contrail_fedora_repo]
name=Contrail Fedora Repo
baseurl=$__contrail_fedora_path__
enabled=1
gpgcheck=0
""")

CONTRAIL_PKGS_TEMPL = string.Template("""
[contrail_pkgs_repo]
name=Contrail Demo Repo
baseurl=$__contrail_pkgs_path__
enabled=1
gpgcheck=0
""")

INSTALLER_DIR = '/opt/contrail/contrail_installer'

try:
    from fabric.api import env, parallel, roles, run, settings, sudo, task, cd, local
    from fabric.state import output
    from fabric.operations import get, put, reboot
except ImportError:
    _tgt_path = os.path.abspath(INSTALLER_DIR)
    subprocess.call(
        "sudo pip-python install %s/contrail_setup_utils/pycrypto-2.6.tar.gz" %
        (_tgt_path), shell=True)
    subprocess.call(
        "sudo pip-python install %s/contrail_setup_utils/paramiko-1.9.0.tar.gz" %
        (_tgt_path), shell=True)
    subprocess.call(
        "sudo pip-python install %s/contrail_setup_utils/Fabric-1.5.1.tar.gz" %
        (_tgt_path), shell=True)
    from fabric.api import env, parallel, roles, run, settings, sudo, task, cd, local
    from fabric.state import output
    from fabric.operations import get, put, reboot


class CleanupMachines:

    def __init__(self, args=''):
        self.parse_args(args)
#        config = ConfigParser.ConfigParser()
#        if self.args.single_node:
#            self.json_data= self._create_prov_data()
#            self.contrail_pkgs_repo='http://10.204.216.51/cobbler/repo_mirror/contrail_pkgs_repo'
#            self.contrail_fedora_repo= 'http://10.204.216.51/cobbler/repo_mirror/combined_new_repo'
#        elif self.args.ini_file:
#            config.read(self.args.ini_file)
#            self.provFile=config.get('Basic','provFile')
#
#            self.contrail_pkgs_repo= config.get('Basic', 'contrail_pkgs_repo')
#            self.contrail_fedora_repo= config.get('Basic', 'contrail_fedora_repo')
#            self.json_data= self._read_provFile(self.provFile)
# end if
#
#        self._temp_dir_name = tempfile.mkdtemp()
#        self.reboot={}
#        for host in self.json_data['hosts'] :
#            host_ip=str(IPNetwork(host['ip']).ip)
#            self.reboot[host_ip] = True
#

    def parse_args(self, args):

        defaults = {
            'username': 'root',
            'password': 'contrail123',
            'dont_reboot': False,
            'clear_old_cert': False,
        }
        parser = argparse.ArgumentParser()
        parser.set_defaults(**defaults)
        parser.add_argument('-n', '--node', dest='node',
                            help='IP of the node')
        parser.add_argument('-u', '--username', dest='username',
                            help='username')
        parser.add_argument('-p', '--password', dest='password',
                            help='password')
        parser.add_argument(
            '-r', "--dont_reboot", dest="dont_reboot", action='store_true',
            help="Don't reboot agent nodes, User will reboot manually before testing")
        parser.add_argument(
            '-c', "--clear_old_certs", dest="clear_old_certs", action='store_true',
            help="Clear all pem files which might prevent nova access")

        self.args = parser.parse_args()
    # end parse_args

    def cleanup_pkgs(self):
        run('sudo yum -y -x contrail-fabric-utils -x contrail-install-packages remove contrail* *openstack* *quantum* *nova* *glance* *keystone* *cinder* libvirt* hiredis-py irond euca2ools redis-py supervisor xmltodict zookeeper*')
        with cd('/etc/'):
            run('sudo rm -rf glance/ cinder/ openstack_dashboard/ contrail/ keystone/ quantum/ nova/  /var/lib/mysql /var/lib/nova /var/lib/quantum /var/lib/keystone /var/lib/keystone /var/lib/glance /var/lib/cassandra ')
    # end cleanup_pkgs

    def setup(self):
        with settings(
            host_string='%s@%s' % (self.args.username, self.args.node),
                password=self.args.password, warn_only=True):
            self.cleanup_pkgs()
            if not self.args.dont_reboot:
                reboot()
    # end setup


if __name__ == "__main__":
    x = CleanupMachines(' '.join(sys.argv[1:]))
    x.setup()
