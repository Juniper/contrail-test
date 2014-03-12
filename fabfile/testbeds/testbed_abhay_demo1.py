from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.51.12'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = '1.1.1.0/24'

host_build = 'vidyadharj@10.84.5.111'

env.roledefs = {
    'all': [host1],
    'cfgm': [host1],
    'openstack': [host1],
    'collector': [host1],
    'webui': [host1],
    'control': [host1],
    'compute': [host1],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['10.84.51.12']
}

env.passwords = {
    host1: 'c0ntrail123',
}

env.test_repo_dir='/home/vidyadharj/build/code/test'
env.mail_from='abhayj@juniper.net'
env.mail_to='abhayj@juniper.net'
