from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.204.216.31'
host2 = 'root@10.204.216.30'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.46.0/24"

host_build = 'root@10.204.216.31'

env.roledefs = {
    'all': [host1,host2],
    'cfgm': [host1],
    'control': [host1],
    'compute': [host1, host2],
    'collector': [host1],
    'webui': [host1],
    'build': [host_build],
    'database': [host1],
}

env.hostnames = {
    'all': ['nodea35.englab.juniper.net', 'nodea34.englab.juniper.net']
}


env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host_build: 'c0ntrail123',

}

env.test_repo_dir='/root/test'
env.mail_from='smusuvathi@juniper.net'
env.mail_to='smusuvathi@juniper.net'
