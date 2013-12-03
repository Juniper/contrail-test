from fabric.api import env

host1 = 'root@10.84.14.1'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = '1.1.1.0/24'

host_build = 'ajayhn@10.84.5.101'

env.roledefs = {
    'all': [host1],
    'cfgm': [host1],
    'collector': [host1],
    'webui': [host1],
    'control': [host1],
    'compute': [host1],
    'database': [host1],
    'build': [host_build],
}

env.passwords = {
    host1: 'c0ntrail123',

    host_build: 'c0ntrail123',
}

env.hostnames = {
    'all': ['a5s1']
}
