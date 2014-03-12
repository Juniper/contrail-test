from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'
#service_token = '53468cf7552bbdc3b94f'

host1 = 'root@10.84.9.44'
host2 = 'root@10.84.13.35'
host3 = 'root@10.84.13.36'

#ext_routers = [('mx1', '10.84.11.253'), ('mx2', '10.84.11.252')]
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.44.0/24"

host_build = 'praneetb@10.84.5.111'

env.roledefs = {
    'all': [host1, host2, host3],
    'openstack': [host1],
    'cfgm': [host2],
    'control': [host3],
    'compute': [host3],
    'collector': [host2],
    'webui': [host2],
    'database': [host2],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a3s44','a6s35', 'a6s36']
}


env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',

    host_build: 'c0ntrail123',
}

env.test_repo_dir='/home/praneetb/build/test'
env.mail_from='praneetb@juniper.net'
env.mail_to='praneetb@juniper.net'
multi_tenancy=True
