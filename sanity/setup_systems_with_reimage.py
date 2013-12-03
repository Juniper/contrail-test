import tempfile
import sys
import string
import ConfigParser, argparse
import socket
import json
from netaddr import *
import re
import xml.etree.ElementTree as ET
import os
import subprocess

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

INSTALLER_DIR='/opt/contrail/contrail_installer'

try:
    from fabric.api import env, parallel, roles, run, settings, sudo, task, cd, local
    from fabric.state import output
    from fabric.operations import get, put, reboot
except ImportError:
    _tgt_path = os.path.abspath(INSTALLER_DIR)
    subprocess.call("sudo pip-python install %s/contrail_setup_utils/pycrypto-2.6.tar.gz" %(_tgt_path), shell=True)
    subprocess.call("sudo pip-python install %s/contrail_setup_utils/paramiko-1.9.0.tar.gz" %(_tgt_path), shell=True)
    subprocess.call("sudo pip-python install %s/contrail_setup_utils/Fabric-1.5.1.tar.gz" %(_tgt_path), shell=True)
    from fabric.api import env, parallel, roles, run, settings, sudo, task, cd, local
    from fabric.state import output
    from fabric.operations import get, put, reboot

env.disable_known_hosts= True

class SetupMachines:
    def __init__(self, args = ''):
        self.parse_args (args)
        config = ConfigParser.ConfigParser()
        # the fabfile_path is used to run the fab script
        # even the testbed.py file needs to be copied to that location
        self.fab_dir= self.args.fabfile_path
        testbed_file= self.args.testbed_file
        local("cp %s %s/fabfile/testbeds/testbed.py" %(testbed_file, self.fab_dir))
        f=os.path.realpath(__file__)
        self.sanity_path=os.path.dirname(f)
        local("cp %s %s/testbed.py" %(testbed_file, self.sanity_path))
        import testbed
        local("/bin/fab -f %s/fabfile setup_test_env"%self.fab_dir)
        #if self.args.single_node:
        #    self.json_data= self._create_prov_data()
        #    self.contrail_pkgs_repo='http://10.204.216.51/cobbler/repo_mirror/contrail_pkgs_repo'
        #    self.contrail_fedora_repo= 'http://10.204.216.51/cobbler/repo_mirror/combined_new_repo'
        self.ini_file= '%s/sanity/sanity_params.ini' %(env.test_repo_dir) 
        print self.ini_file
        config.read(self.ini_file)
        self.provFile=config.get('Basic','provFile')
        self.contrail_pkgs_repo= config.get('Basic', 'contrail_pkgs_repo')
        self.contrail_fedora_repo= config.get('Basic', 'contrail_fedora_repo')
        self.json_data= self._read_provFile(self.provFile)
        #end if
        
        self._temp_dir_name = tempfile.mkdtemp()
        self.reboot={}
        for host in self.json_data['hosts'] :
            host_ip=str(IPNetwork(host['ip']).ip)
            self.reboot[host_ip] = True
       
    
    def parse_args (self, args):

        defaults= {
            'ini_file' : 'params.ini',
            'skip_install' : False,
            'dont_reboot' : False,
            'username' : 'root',
            'password' : 'contrail123',
            'single_node' : None,
            'fab_path' : "fabfile_path",
            'testbed_file' : "testbed_file"
        }
        parser = argparse.ArgumentParser()
        parser.set_defaults(**defaults)
        # Removing the -i option as ini file is no lonegr used as a input
        #parser.add_argument('-i', "--ini_file", dest="ini_file",
        #    help = "Init file which has reference to setup and testcase details") 
        parser.add_argument('-p', "--skip_install", dest="skip_install", action='store_true',
                        help = "Skip installing latest packages from repo")
#        parser.add_argument('-s', "--single_node",dest= "single_node", 
#                     help = "IP of the All-in-one Single node setup. Ignores the (-i)ini_file option if supplied")
        parser.add_argument('-u', '--username', dest= 'username', 
                    help= 'username of the Single node. Default is root')
        parser.add_argument('-pw', '--password', dest= 'password', 
                    help= 'password of the Single node. Default is contrail123')
        parser.add_argument('-r', "--dont_reboot", dest="dont_reboot", action='store_true',
                        help = "Don't reboot agent nodes, User will reboot manually before testing")
        parser.add_argument('-f', "--fab_file path", dest="fabfile_path",
                        help = "Provide the path of the fabfile from fabric-utils")
        parser.add_argument('-t', "--testbed file", dest="testbed_file",
                        help = "Provide the full path of your testbed_xyz.py")
        self.args=parser.parse_args()
    #end parse_args

    def _read_provFile(self, provFile):
        prov_file = open( provFile, 'r')
        prov_data = prov_file.read()
        json_data=json.loads(prov_data)
        self.cfgmIP=''
        self.computeIPs=[]
        self.bgpIPs=[]
        self.hostIPs=[]
        for host in json_data['hosts'] :
            hostIP=str(IPNetwork(host['ip']).ip)
            self.hostIPs.append(hostIP)
            roles= host["roles"]
            for role in roles :
                if role['type'] == 'cfgm':
                    self.cfgmIP= hostIP
                    self.masterhost=self.cfgmIP
                    self.hostname=host['name']
                if role['type']== 'compute':
                    self.computeIPs.append(hostIP)
                if role['type'] == 'bgp':
                    self.bgpIPs.append(hostIP)
            #end for
        #end for    
        return json.loads(prov_data)
    #end _read_provision_data 
    
    def _create_prov_data(self):
        ''' Creates json data for a single node only.
        
        '''
        single_node= self.args.single_node
        self.cfgmIP= single_node
        self.bgpIPs=[single_node,single_node]
        self.computeIPs= [single_node]
        self.hostIPs= [single_node]
        json_data= {}
        hostname= socket.gethostbyaddr(single_node)[0]
        json_data['hosts']= [{
            'ip' : single_node,
            'name' : hostname,
            'username' : self.args.username,
            'password' : self.args.password,
            'roles' : [
            {"params": {"collector": hostname, "cfgm": hostname}, "type": "bgp"},
            {"params": {"bgp": [hostname, hostname],"cfgm": hostname, "collector": hostname}, "type": "compute"},
            {"params": {"collector": hostname}, "type": "cfgm"},
            {"params": {"cfgm": hostname}, "type": "webui"},
            { "type": "collector"}
            ]
            }]
        return json_data
    #end _create_prov_data
            
    
    def _template_substitute(self, template, vals):
        data = template.safe_substitute(vals)
        return data
    #end _template_substitute

    def _template_substitute_write(self, template, vals, filename):
        data = self._template_substitute(template, vals)
        outfile = open(filename, 'w')
        outfile.write(data)
        outfile.close()
    #end _template_substitute_write
    
    def setup_repo(self):
        with cd("/etc/yum.repos.d/"):
#            ls_out = run("find . -maxdepth 1 -type f -name '*'", capture = True)
            ls_out = run("find . -maxdepth 1 -type f -name '*'")
            print "output : " + ls_out
            existing_repos = [ repo for repo in ls_out.split() if not re.match('./contrail*', repo) ]

            if existing_repos:
                with settings(warn_only = True):
                    run("sudo mkdir saved-repos")
            for repo in existing_repos:
                if repo == 'saved-repos':
                    continue
                run("sudo mv %s saved-repos" %(repo))

            self._template_substitute_write(CONTRAIL_FEDORA_TEMPL,
                 {'__contrail_fedora_path__': self.contrail_fedora_repo},
                 '%s/contrail_fedora.repo' %(self._temp_dir_name))
            self._template_substitute_write(CONTRAIL_PKGS_TEMPL,
                 {'__contrail_pkgs_path__': self.contrail_pkgs_repo},
                 '%s/contrail_pkgs.repo' %(self._temp_dir_name))
#            run("sudo mv %s/contrail_fedora.repo ." %(self._temp_dir_name))
#            run("sudo mv %s/contrail_pkgs.repo ." %(self._temp_dir_name))
            put("%s/contrail_pkgs.repo" %(self._temp_dir_name), 
                "/etc/yum.repos.d")
            put("%s/contrail_fedora.repo" %(self._temp_dir_name), 
                "/etc/yum.repos.d")

#        with lcd("%s" %(self._setup_tgt_path)):
#            local("sudo createrepo .")
    #end setup_repo
   
    def install_or_upgrade_pkg(self, package):
        with settings(warn_only=False):
            try:
                run("yum list installed | grep %s" %(package))
                # If no exception above, blindly update the packge
                run("yum -y update %s" %(package))
            except SystemExit as e:
                run("yum -y install %s" %(package))
    #end install_or_upgrade_pkg
   
    def setup_cgroup_entry(self):
        try:
            ret = run("sudo grep -q '^cgroup_device_acl' /etc/libvirt/qemu.conf")
        except SystemExit as e:
            run('sudo echo \'cgroup_device_acl = [\' >> /etc/libvirt/qemu.conf')
            run('sudo echo \'    "/dev/null", "/dev/full", "/dev/zero",\' >> /etc/libvirt/qemu.conf')
            run('sudo echo \'    "/dev/random", "/dev/urandom",\' >> /etc/libvirt/qemu.conf')
            run('sudo echo \'    "/dev/ptmx", "/dev/kvm", "/dev/kqemu",\' >> /etc/libvirt/qemu.conf')
            run('sudo echo \'    "/dev/rtc", "/dev/hpet","/dev/net/tun",\' >> /etc/libvirt/qemu.conf')
            run('sudo echo \']\' >> /etc/libvirt/qemu.conf') 
    #end setup_cgroup_entry 
    
    def install_packages(self, host):
        run("sudo yum clean all")
        host_ip= str(IPNetwork(host['ip']).ip)
        role_types=[ role['type'] for role in host['roles'] ]
        
        common_packages=[ 'contrail-setup'] 
        [self.install_or_upgrade_pkg(package) for package in common_packages]
        
        if 'bgp' in role_types:
            self.install_or_upgrade_pkg('contrail-control')
            self.install_or_upgrade_pkg('contrail-libs')
        if 'cfgm' in role_types : 
            packages=['openstack-nova', 'openstack-quantum','openstack-cinder',
                    'openstack-glance', 'openstack-keystone', 'contrail-api',
                    'openstack-quantum-contrail', 'mysql','qpid-cpp-server', 
                    'openstack-dashboard', 'mysql-server', 'contrail-libs', 'openstack-nova-novncproxy']
            for package in packages:
                self.install_or_upgrade_pkg(package)
        if 'collector' in role_types :
            self.install_or_upgrade_pkg('contrail-analytics')
#        if 'compute' in role_types and 'cfgm' not in role_types :
        if 'compute' in role_types :
            packages=['contrail-agent', 'openstack-utils', 'openstack-nova-compute', 
                    'contrail-libs' ]
            for package in packages:
                self.install_or_upgrade_pkg(package)
            services=['contrail-vrouter', 'openstack-nova-compute']
            [self.enable_services(service) for service in services]
        if 'collector' in role_types : 
            packages=['contrail-analytics']
            [self.install_or_upgrade_pkg(package) for package in packages]
        if 'webui' in role_types : 
            packages=['contrail-webui']
            [self.install_or_upgrade_pkg(package) for package in packages]            
    #end install_packages        
   
    def enable_services(self, service):
        run('sudo chkconfig %s on' %(service))
    #end def
    
    def check_and_reboot(self, host_ip):
        if self.reboot[host_ip]:
            print "rebooting %s" %(host_ip)
            run('reboot')
    
    def clean_remnants(self, host):
        host_ip= str(IPNetwork(host['ip']).ip)
        role_types= [ role['type'] for role in host['roles'] ]
       
         # Defining a list of DBs
        DBs =['nova', 'mysql', 'keystone', 'glance', 'cinder']
        [self.clean_DB(database) for database in DBs]
        
        # Clearing the tokens
        run('sudo rm -f /etc/contrail/mysql.token')
        run('sudo rm -f /etc/contrail/service.token')
        run('sudo rm -f /etc/contrail/keystonerc')
        run('sudo rm -f /var/lib/glance/images/*') 
         # Defining a list of all services
        all_services =['redis', 'mysqld', 'openstack-nova-novncproxy', 'qpidd', 'ifmap', 'openstack-cinder-volume', 'openstack-cinder-scheduler', 'openstack-cinder-api', 'openstack-glance-registry', 'openstack-glance-api', 'openstack-nova-xvpvncproxy', 'openstack-nova-scheduler', 'openstack-nova-objectstore', 'openstack-nova-metadata-api', 'openstack-nova-consoleauth', 'openstack-nova-console', 'openstack-nova-compute', 'openstack-nova-cert', 'openstack-nova-api', 'contrail-vncserver', 'contrail-analyzer', 'puppetmaster', 'puppetagent', 'contrail-opserver', 'openstack-keystone', 'contrail-qe', 'contrail-collector', 'quantum-server', 'contrail-svc-monitor', 'contrail-schema', 'contrail-control', 'contrail-api', 'contrail-webui', 'contrail-webui-middleware', 'contrail-vrouter']
        self.disable_stop_services(all_services)
        
        # Not all of these maybe relevant, but keeping these cmds as is
        if 'cfgm' in role_types :
            try : 
                run('sudo rm -rf /var/lib/nova/tmp/nova-iptables')
                run('sudo rm -rf /var/lib/libvirt/qemu/instance*')
                run('sudo rm -rf /var/log/libvirt/qemu/instance*')
                run('sudo rm -rf /var/lib/nova/instances/instance-*')
                run('sudo rm -rf /etc/libvirt/nwfilter/nova-instance*')
                run('sudo rm -rf /var/log/libvirt/qemu/inst*')
                run('sudo rm -rf /etc/libvirt/qemu/inst*')
                run('sudo rm -rf /var/lib/nova/instances/_base/*')
            except SystemExit as e:
                print "Failure of one or more of these cmds are ok"
        elif 'compute' in role_types:
            try:
                run('sudo systemctl stop  openstack-nova-compute.service')
                run('sudo rm -rf /var/lib/nova/tmp/nova-iptables')
                run('sudo rm -rf /var/log/libvirt/qemu/instance*')
                run('sudo rm -rf /var/lib/nova/instances/instance-*')
                run('sudo rm -rf /var/log/libvirt/qemu/inst*')
                run('sudo rm -rf /etc/libvirt/nwfilter/nova-instance*')
            except SystemExit as e:
                print "Failure of one or more of these cmds are ok"
    #end clean_remnants

    def disable_stop_services(self, services):
        service_cmd=''  
        for service in services :
            service_cmd= service_cmd + service+'.service '
        run('sudo systemctl disable %s ' %(service_cmd))
        run('sudo systemctl stop %s ' %(service_cmd))
    #end def

    def clean_DB(self, database):
     # Getting the token
        token=run('cat /etc/contrail/mysql.token')
        print "Token is :%s:" %(token)
        run('mysql -u root --password=%s -e \'drop database %s;\''  %(token, database))
    #end def    

    def enable_api_server_reset(self, host):
        try :
            run('sudo sed -i \'s/api_server.conf$/api_server.conf --reset_config/\' \
                    /usr/lib/systemd/system/contrail-api.service')
            run('sudo systemctl --system daemon-reload')
        except SystemExit as e:
            print "Failure of one or more of these cmds are ok"
    
    def run_fab_scripts(self):
        local("/bin/fab -f %s/fabfile setup_database"%self.fab_dir)
        local("/bin/fab -f %s/fabfile setup_cfgm"%self.fab_dir)
        local("/bin/fab -f %s/fabfile setup_control"%self.fab_dir)
        local("/bin/fab -f %s/fabfile setup_vrouter"%self.fab_dir)
        local("/bin/fab -f %s/fabfile setup_collector"%self.fab_dir)
        local("/bin/fab -f %s/fabfile setup_webui"%self.fab_dir)
        local("/bin/fab -f %s/fabfile prov_control_bgp"%self.fab_dir)
        local("/bin/fab -f %s/fabfile setup_test_env"%self.fab_dir)
        local("/bin/fab -f %s/fabfile all_reboot"%self.fab_dir)
    
    def set_etc_hosts(self):
        self.hostlist=''
        for host in self.json_data['hosts']:
            host_ip=str(IPNetwork(host['ip']).ip)
            self.hostlist+= '%s %s\n' %(host_ip, host['name'])
        print self.hostlist
        for host in self.json_data['hosts']:
            host_ip=str(IPNetwork(host['ip']).ip)
            with settings( host_string='%s@%s' %(host['username'], host_ip),
                       password= host['password'], warn_only=True):
                run('/bin/echo \"%s\" >> /etc/hosts' %(self.hostlist) )
        
    def setup(self):
        cfgm=None
        self.set_etc_hosts()
        self.run_fab_scripts()
            
    #end setup

if __name__ == "__main__":
    x = SetupMachines(' '.join (sys.argv[1:]))
    x.setup()
