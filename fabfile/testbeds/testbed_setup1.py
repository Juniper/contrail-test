from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.11.2'
host2 = 'root@10.84.11.3'
host3 = 'root@10.84.11.4'
host4 = 'root@10.84.11.5'
host5 = 'root@10.84.11.6'

ext_routers = [('mx1', '10.84.11.253'), ('mx2', '10.84.11.252')]
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.41.0/24"

host_build = 'ajayhn@10.84.5.101'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5],
    'cfgm': [host1],
    'control': [host2, host3],
    'compute': [host4, host5],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a3s31', 'a3s30', 'a3s29','a3s28', 'a3s27']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',
    host5: 'c0ntrail123',

    host_build: 'c0ntrail123',
}
