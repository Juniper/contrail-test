from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.204.216.42'
host2 = 'root@10.204.216.40'

ext_routers = [('mx1', '10.204.216.253')]
router_asn = 64512
public_vn_rtgt = 10003
public_vn_subnet = "10.204.219.16/28"

host_build = 'chhandak@10.84.5.101'

env.roledefs = {
    'all': [host1, host2],
    'cfgm': [host1],
    'control': [host1, host2],
    'compute': [host1, host2],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodea4', 'nodea2']
}


env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',

    host_build: 'contrail123',
}

env.test_repo_dir='/homes/chhandak/test'
env.mail_from='chhandak@juniper.net'
env.mail_to='chhandak@juniper.net'
