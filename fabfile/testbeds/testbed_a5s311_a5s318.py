import os
from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.14.31'
host2 = 'root@10.84.14.32'
host3 = 'root@10.84.14.33'
host4 = 'root@10.84.14.34'
host5 = 'root@10.84.14.35'
host6 = 'root@10.84.14.36'
host7 = 'root@10.84.14.37'
host8 = 'root@10.84.14.38'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.44.0/24"

host_build = 'contrail@10.84.5.101'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5, host6, host7, host8],
    'cfgm': [host1],
    'control': [host2, host3],
    'compute': [host4, host5, host6, host7, host8],
    'collector': [host1],
    'database': [host1],
    'webui': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a5s311', 'a5s312', 'a5s313','a5s314', 'a5s315', 'a5s316', 'a5s317', 'a5s318']
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
    host_build: 'c0ntrail123',
}

env.test_repo_dir=os.path.expanduser('~/test')
env.mail_from='ijohnson@juniper.net'
env.mail_to='ijohnson@juniper.net'
