from fabric.api import env

host1 = 'root@10.84.7.40'
host2 = 'root@10.84.7.42'
host3 = 'root@10.84.7.28'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = '22.2.1.1/24'

host_build = 'root@10.84.7.40'

env.roledefs = {
    'all': [host1, host2, host3],
    'cfgm': [host1],
    'control': [host1, host2, host3],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
    #'compute': [],
}

env.hostnames = {
    'all': ['a2s40', 'a2s42', 'a2s28']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',

    host_build: 'c0ntrail123',
}
