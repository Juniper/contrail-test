from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.204.217.3'
host2 = 'root@10.204.217.4'
host3 = 'root@10.204.217.5'
host4 = 'root@10.204.216.54'
host5 = 'root@10.204.216.52'

ext_routers = [('mx1', '10.204.216.245')]
router_asn = 64512
public_vn_rtgt = 10005
public_vn_subnet = '10.204.219.48/28'

host_build = 'root@10.204.216.4'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5],
    'cfgm': [host1],
    'webui': [host1],
    'control': [host2, host3],
    'compute': [host4, host5],
    'collector': [host2, host3],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodec18', 'nodec19', 'nodec20', 'nodee1', 'nodef1']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',
    host5: 'c0ntrail123',

    host_build: 'c0ntrail123',
}

env.test_repo_dir='/home/stack/regression_repo/test'
env.mail_from='smusuvathi@juniper.net'
env.mail_to='smusuvathi@juniper.net'
env.log_scenario='Regression'
multi_tenancy=True
