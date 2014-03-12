from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.13.23'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
host_build = 'meghb@10.84.5.111'
database_ttl = 24
database_dir = '/home/cassandra/megh'
collector_syslog_port = 8514

env.roledefs = {
    'all': [host1],
    'cfgm': [host1],
    'collector': [host1],
    'webui': [host1],
    'control': [host1],
    'compute': [host1],
    'database': [host1],
    'openstack': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a6s23']
}

env.passwords = {
    host1: 'c0ntrail123',

    host_build: 'meghb123',
}
env.test_repo_dir = '/home/meghb/build/test'
