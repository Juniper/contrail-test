from fabric.api import env

host1 = 'root@10.204.216.38'
host2 = 'root@10.204.216.5'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10003
public_vn_subnet = '10.204.219.32/28'

host_build = 'vjoshi@10.204.216.37'

env.roledefs = {
    'all': [host1, host2],
    'cfgm': [host1],
    'control': [host1,host2],
    'compute': [host1,host2],
    'collector': [host1],
    'database': [host1],
    'webui': [host1],

    'build': [host_build],
}

env.hostnames = {
    'all': ['nodeb7','nodeb12']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host_build: 'secret',
}

env.test_repo_dir='/homes/vjoshi/test'
env.mail_from='vjoshi@juniper.net'
env.mail_to='vjoshi@juniper.net'

os_username='admin'
os_password='contrail123'
os_tenant_name='admin'
multi_tenancy='True'
env.interface_rename = True
