from fabric.api import env

host1 = 'root@10.204.216.45'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10003
public_vn_subnet = '10.204.219.64/29'

host_build = 'stack@10.204.216.37'

env.roledefs = {
    'all': [host1],
    'cfgm': [host1],
    'control': [host1],
    'compute': [host1],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodea7']
}

env.passwords = {
    host1: 'c0ntrail123',
    host_build: 'contrail123',
}

env.ostypes = {
   host1 : 'fedora'
}

# Folder where you have checked out the field-test git repo
env.test_repo_dir = '/homes/vjoshi/cloudscaling/field-test'

env.mail_to = 'vjoshi@juniper.net'
env.mail_server = '10.204.216.49'
env.mail_port = '25'
env.log_scenario = 'Openstack Single-Node Sanity'
multi_tenancy=False

env.interface_rename = True
