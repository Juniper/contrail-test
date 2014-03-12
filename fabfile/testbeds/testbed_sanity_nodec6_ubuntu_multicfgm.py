from fabric.api import env

host1 = 'root@10.204.216.63'
host2 = 'root@10.204.216.64'
host3 = 'root@10.204.216.65'
host4 = 'root@10.204.216.66'
host5 = 'root@10.204.216.67'

ext_routers = [('mx1', '10.204.216.253')]
router_asn = 64512
public_vn_rtgt = 10003
public_vn_subnet = "10.204.219.32/29"

host_build = 'stack@10.204.216.49'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5],
    'cfgm': [host1, host2, host3],
    'openstack': [host1],
    'control': [host2, host3],
    'compute': [host4, host5],
    'collector': [host1, host3],
    'webui': [host2],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodec6', 'nodec7', 'nodec8', 'nodec9', 'nodec10']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',
    host5: 'c0ntrail123',

    host_build: 'contrail123',
}

env.ostypes = {
    host1:'ubuntu',
    host2:'ubuntu',
    host3:'ubuntu',
    host4:'ubuntu',
    host5:'ubuntu',
}

env.test_repo_dir= "/home/stack/multi_node_1/contrail-test"
env.mail_to='dl-contrail-sw@juniper.net'
multi_tenancy=True
env.interface_rename= True
env.encap_priority= "'MPLSoUDP','MPLSoGRE','VXLAN'"
