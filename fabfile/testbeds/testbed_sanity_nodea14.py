from fabric.api import env

host1 = 'root@10.204.216.10'
host2 = 'root@10.204.216.9'
host3 = 'root@10.204.216.8'
host4 = 'root@10.204.216.2'
host5 = 'root@10.204.216.1'


ext_routers = [('mx1', '10.204.216.253')]
router_asn = 64512
public_vn_rtgt = 10003
public_vn_subnet = "10.204.219.16/28"

host_build = 'stack@10.204.216.49'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5],
    'cfgm': [host1],
    'openstack': [host1],
    'control': [host2, host3],
    'compute': [host4, host5],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodea14', 'nodea13', 'nodea12', 'nodeb9', 'nodeb8']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',
    host5: 'c0ntrail123',

    host_build: 'contrail123',
}
env.test_repo_dir = "/home/stack/multi_node/test"
env.mail_from='vjoshi@juniper.net'
env.mail_to='dl-contrail-sw@juniper.net'
env.log_scenario='CentOS Openstack Five-Node Sanity'
multi_tenancy=True
env.interface_rename = True
