from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.13.35'
host1 = 'root@10.84.13.36'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = '1.1.1.0/24'

host_build = 'praneet@10.84.5.111'

env.roledefs = {
    'all': [host1, host2],
    'cfgm': [host1],
    'openstack': [host1],
    'collector': [host1],
    'webui': [host1],
    'control': [host1],
    'compute': [host2],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a6s35', 'a6s36']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
}

env.test_repo_dir='/home/praneetb/build/test'
env.mail_from='praneetb@juniper.net'
env.mail_to='praneetb@juniper.net'
multi_tenancy=True
