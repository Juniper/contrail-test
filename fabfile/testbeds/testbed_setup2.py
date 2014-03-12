from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.12.11'
host2 = 'root@10.84.12.12'
host3 = 'root@10.84.12.13'
host4 = 'root@10.84.12.14'
host5 = 'root@10.84.12.15'

ext_routers = [('mx1', '10.84.12.253'), ('mx2', '10.84.12.252')]
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.42.0/24"

host_build = 'ajayhn@10.84.5.101'

#host1 & host5 have more memory - hence they are made compute
env.roledefs = {
    'all': [host1, host2, host3, host4, host5],
    'cfgm':      [host2],
    'openstack': [host2],
    'webui':     [host2],
    'control':   [host3, host4],
    'collector': [host3, host4],
    'database':  [host3, host4],
    'compute':   [host1, host5],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a3s43', 'a3s42', 'a3s41','a3s40', 'a3s39']
}


env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',
    host5: 'c0ntrail123',

    host_build: 'c0ntrail123',
}

database_dir = '/home/cassandra'
database_ttl = 168

env.test_repo_dir = '/home/rajreddy/test'
