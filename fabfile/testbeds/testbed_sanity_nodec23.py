from fabric.api import env

host1 = 'root@10.204.217.8'

ext_routers = [('mx1', '10.204.216.253')]
router_asn = 64512
public_vn_rtgt = 10003
public_vn_subnet = "10.204.219.24/29"

host_build = 'stack@10.204.216.49'

env.roledefs = {
    'all': [host1],
    'cfgm': [host1],
    'openstack': [host1],
    'control': [host1],
    'compute': [host1],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodec23']
}

env.passwords = {
    host1: 'c0ntrail123',
    host_build: 'contrail123',
}

env.test_repo_dir='/home/stack/centos_openstack_sanity/contrail-test'
env.mail_from='vjoshi@juniper.net'
env.mail_to='dl-contrail-sw@juniper.net'
env.log_scenario='CentOS(Openstack) Single-Node Sanity'
multi_tenancy=True
env.interface_rename = False 
env.encap_priority =  "'MPLSoUDP','MPLSoGRE','VXLAN'"
