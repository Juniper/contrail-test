from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.204.216.7'
host2 = 'root@10.204.216.14'
host3 = 'root@10.204.216.25'
host4 = 'root@10.204.216.15'
host5 = 'root@10.204.216.68'
host6 = 'root@10.204.216.69'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.46.0/24"

host_build = 'sandipd@10.204.216.4'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5, host6],
    'cfgm': [host1],
    'control': [host2, host3],
    'compute': [host4, host5, host6],
    'collector': [host2,host3],
    'webui': [host1],
    'database': [host2,host3],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodea11', 'nodea18', 'nodea29','nodea19', 'nodec11', 'nodec12']
}


env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',
    host5: 'c0ntrail123',
    host6: 'c0ntrail123',

    host_build: 'c0ntrail123',
}

env.test_repo_dir='/home/sandipd/multinode/test'
env.mail_from='sandipd@juniper.net'
env.mail_to='sandipd@juniper.net'
multi_tenancy=True
