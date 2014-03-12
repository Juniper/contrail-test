from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.13.39'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000

host_build = 'cdmishra@10.84.5.111'

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

env.hostnames = {
    'all': ['a6s39']
}

env.passwords = {
    host1: 'c0ntrail123',

    host_build: 'cdmishra123',
}

env.test_repo_dir='/home/cdmishra/test'
env.mail_from='cdmishra@juniper.net'
env.mail_to='cdmishra@juniper.net'
