from fabric.api import env

host1 = 'root@10.204.216.23'
host2 = 'root@10.204.216.46'
host3 = 'root@10.204.216.38'

host_build = 'mnaik@nodeb11'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = '10.1.1.0/24'


env.roledefs = {
    'all': [host1, host2, host3],
    'cfgm': [host3],
    'openstack': [host3],
    'control': [host1, host2],
    'compute': [host1, host2],
    'collector': [host1, host2],
    'webui': [host3],
    'database': [host1, host2],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodea27', 'nodea8', 'nodeb7']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host_build: 'secret',
}

env.test_repo_dir='/home/mnaik/test'
env.mail_from='mnaik@juniper.net'
env.mail_to='mnaik@juniper.net'
