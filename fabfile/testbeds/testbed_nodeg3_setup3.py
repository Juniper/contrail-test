from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.204.217.42'
host2 = 'root@10.204.217.43'
host3 = 'root@10.204.217.44'

host_build = 'ajayhn@10.84.5.101'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = '10.1.1.0/24'


env.roledefs = {
    'all': [host1, host2, host3],
    'cfgm': [host2, host3],
    'openstack': [host2],
    'control': [host2, host3],
    'compute': [host1],
    'collector': [host2, host3],
    'webui': [host2],
    'database': [host2, host3],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodeg2', 'nodeg3', 'nodeg4']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host_build: 'c0ntrail123',
}

