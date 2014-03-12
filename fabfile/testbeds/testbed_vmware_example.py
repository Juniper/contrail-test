from fabric.api import env

#Management ip addresses of hosts in the cluster
host1 = 'root@10.204.217.7'
#host2 = 'root@10.204.217.57'

#External routers if any
#for eg. 
#ext_routers = [('mx1', '10.204.216.253')]
ext_routers = []

#Autonomous system number
router_asn = 64512

#Host from which the fab commands are triggered to install and provision
host_build = 'vjoshi@10.204.216.56'

#Role definition of the hosts.
env.roledefs = {
#    'all': [host1,host2],
    'all': [host1],
    'cfgm': [host1],
    'openstack': [host1],
    'control': [host1],
    'compute': [host1],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
}

#Openstack admin password
env.openstack_admin_password = 'contrail123'

env.ostypes = { 
    host1:'ubuntu'
}

#Hostnames
env.hostnames = {
#    'all': ['nodec22', 'nodeg17']
    'all': ['nodec22']
}

env.password = 'c0ntrial123'
#Passwords of each host
env.passwords = {
    host1: 'c0ntrail123',
#    host2: 'c0ntrail123',


    host_build: 'secret',
}

compute_vm = {
    host1: { 'esxi': {'ip': '10.204.216.35',
                      'username': 'root',
                      'password': 'c0ntrail123',
                      'uplink_nic': 'vmnic2',
                      'vswitch' : 'vSwitch0',
                      'vm_port_group' : 'contrail-compute1-fab-pg',
                     },
             'vm_name' : 'Fedora-Compute-VM1',
             'vmdk' : 'Fedora-Compute-VM1-disk1.vmdk',
             'vswitch': 'vSwitch1',
             'port_group' : 'contrail-compute1-pg',
    },
}
            
             

#OPTIONAL BONDING CONFIGURATION
#==============================
#Inferface Bonding
#bond= {
#    host1 : { 'name': 'bond0', 'member': ['p2p0p0','p2p0p1','p2p0p2','p2p0p3'], 'mode':'balance-xor' },
#}

#OPTIONAL SEPARATION OF MANAGEMENT AND CONTROL + DATA
#====================================================
#Control Interface
#control = {
#    host1 : { 'ip': '192.168.10.1/24', 'gw' : '192.168.10.254', 'device':'eth0' },
#}

#Data Interface
#data = {
#    host1 : { 'ip': '192.161.10.1/24', 'gw' : '192.161.10.254', 'device':'bond0' },
#}

#To disable installing contrail interface rename package
#env.interface_rename = False

#To enable multi-tenancy feature
#multi_tenancy = True

#To enable haproxy feature
#haproxy = True

#To Enable prallel execution of task in multiple nodes
#do_parallel = True
env.test_repo_dir='/homes/vjoshi/node22-17/test'
env.mail_from='vjoshi@juniper.net'
env.mail_to='vjoshi@juniper.net'
env.log_scenario='Single-Node Sanity'
