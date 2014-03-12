from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.14.6'
host2 = 'root@10.84.14.7'
host3 = 'root@10.84.14.8'
host4 = 'root@10.84.14.9'
host5 = 'root@10.84.14.10'

#ext_routers = [('mx1', '10.84.14.253'), ('mx2', '10.84.14.252')]
ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.44.0/24"

host_build = 'contrail@10.84.5.101'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5],
    'cfgm': [host1],
    'openstack': [host1],
    'control': [host2, host3],
    'compute': [host4, host5],
    'collector': [host1],
    'database': [host1],
    'webui': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a5s6', 'a5s7', 'a5s8','a5s9', 'a5s10']
}


env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',
    host5: 'c0ntrail123',
    host_build: 'c0ntrail123',
}

env.test_repo_dir='/home/ijohnson/test'
env.mail_from='ijohnson@juniper.net'
env.mail_to='ijohnson@juniper.net'
