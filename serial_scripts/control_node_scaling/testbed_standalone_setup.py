from fabric.api import env

host1 = 'root@10.84.7.39'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = '33.2.1.1/24'

host_build = 'root@10.84.7.39'

env.roledefs = {
    'all': [host1],
    'cfgm': [host1],
    'control': [host1],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
    #'compute': [],
}

env.hostnames = {
    'all': ['a2s39']
}

env.passwords = {
    host1: 'c0ntrail123',

    host_build: 'c0ntrail123',
}
