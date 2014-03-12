import os
from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.5.42'
host2 = 'root@10.84.5.43'
host3 = 'root@10.84.5.44'
host4 = 'root@10.84.5.45'
host5 = 'root@10.84.24.11'
host6 = 'root@10.84.24.12'
host7 = 'root@10.84.24.13'
host8 = 'root@10.84.24.14'
host9 = 'root@10.84.24.15'

#ext_routers = [('mx1', '10.84.14.253'), ('mx2', '10.84.14.252')]
ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.44.0/24"

host_build = 'contrail@10.84.5.101'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5, host6, host7, host8, host9],
    'cfgm': [host5],
    'control': [host4, host5],
    'compute': [host1, host2, host3, host6, host7, host8, host9],
    'collector': [host5],
    'database': [host5],
    'webui': [host5],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a1s42', 'a1s43', 'a1s44', 'a1s45', 'b4s11', 'b4s12', 'b4s13',
            'b4s14', 'b4s15']
}


env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',
    host5: 'c0ntrail123',
    host6: 'c0ntrail123',
    host7: 'c0ntrail123',
    host8: 'c0ntrail123',
    host9: 'c0ntrail123',
    host_build: 'c0ntrail123',
}

env.test_repo_dir=os.path.expanduser('~/test')
env.mail_from='roque@juniper.net'
env.mail_to='roque@juniper.net'
