from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.13.9'
host2 = 'root@10.84.13.10'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000

host_build = 'rajreddy@10.84.5.103'

env.roledefs = {
    'all': [host1, host2],
    'openstack': [host1],
    'cfgm': [host1],
    'collector': [host1, host2],
    'webui': [host1],
    'control': [host1, host2],
    'compute': [host1, host2],
    'database': [host1, host2],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a6s9', 'a6s10']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host_build: 'rajreddy123',
}

#env.ostypes = {
#      host1: 'fedora',
#      host2: 'fedora',
#}

env.test_repo_dir='/home/rajreddy/test'
