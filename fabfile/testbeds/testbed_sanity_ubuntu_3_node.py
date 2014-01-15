from fabric.api import env

#Management ip addresses of hosts in the cluster
host1 = 'root@10.204.217.58'
host2 = 'root@10.204.217.59'
host3 = 'root@10.204.217.61'

#External routers if any
#for eg. 
#ext_routers = [('mx1', '10.204.216.253')]
ext_routers = [('mx1', '10.204.216.253')]
router_asn = 64512
public_vn_rtgt = 10003
public_vn_subnet = "10.204.219.176/29"


#Host from which the fab commands are triggered to install and provision
host_build = 'stack@10.204.216.49'

#Role definition of the hosts.
env.roledefs = {
    'all': [host1, host2, host3],
    'cfgm': [host1],
    'openstack': [host1],
    'control': [host2, host3],
    'compute': [host2, host3],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodeg18', 'nodeg19', 'nodeg21']
}

env.ostypes = {
    host1:'ubuntu',
    host2:'ubuntu',
    host3:'ubuntu',
}

#Openstack admin password
env.openstack_admin_password = 'contrail123'

env.password = 'c0ntrail123'
#Passwords of each host
env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',

    host_build: 'contrail123',
}

#OPTIONAL BONDING CONFIGURATION
#==============================
#Inferface Bonding
#bond= {
#    host2 : { 'name': 'bond0', 'member': ['p2p0p0','p2p0p1','p2p0p2','p2p0p3'], 'mode':'balance-xor' },
#    host5 : { 'name': 'bond0', 'member': ['p4p0p0','p4p0p1','p4p0p2','p4p0p3'], 'mode':'balance-xor' },
#}

#OPTIONAL SEPARATION OF MANAGEMENT AND CONTROL + DATA
#====================================================
#Control Interface
#control = {
#    host1 : { 'ip': '192.168.10.1/24', 'gw' : '192.168.10.254', 'device':'eth0' },
#    host2 : { 'ip': '192.168.10.2/24', 'gw' : '192.168.10.254', 'device':'p0p25p0' },
#    host3 : { 'ip': '192.168.10.3/24', 'gw' : '192.168.10.254', 'device':'eth0' },
#    host4 : { 'ip': '192.168.10.4/24', 'gw' : '192.168.10.254', 'device':'eth3' },
#    host5 : { 'ip': '192.168.10.5/24', 'gw' : '192.168.10.254', 'device':'p6p0p1' },
#    host6 : { 'ip': '192.168.10.6/24', 'gw' : '192.168.10.254', 'device':'eth0' },
#    host7 : { 'ip': '192.168.10.7/24', 'gw' : '192.168.10.254', 'device':'eth1' },
#    host8 : { 'ip': '192.168.10.8/24', 'gw' : '192.168.10.254', 'device':'eth1' },
#}

#Data Interface
#data = {
#    host2 : { 'ip': '192.161.10.1/24', 'gw' : '192.161.10.254', 'device':'bond0' },
#    host5 : { 'ip': '192.161.10.2/24', 'gw' : '192.161.10.254', 'device':'bond0' },
#}

#To disable installing contrail interface rename package
#env.interface_rename = False

#To enable multi-tenancy feature
#multi_tenancy = True

#To Enable prallel execution of task in multiple nodes
#do_parallel = True
#haproxy = True
env.test_repo_dir='/home/stack/ubuntu_multi_node/test'
env.mail_to='dl-contrail-sw@juniper.net'
env.log_scenario='Ubuntu Three-Node Sanity'
