from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.17.1'
host2 = 'root@10.84.17.2'
host3 = 'root@10.84.17.3'
host4 = 'root@10.84.17.4'
#host5 = 'root@10.84.17.5'

ext_routers = [('mx1', '10.84.17.253'), ('mx2', '10.84.17.252')]
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.46.0/24"
database_dir = '/home/cassandra'

host_build = 'ajayhn@10.84.5.111'

env.roledefs = {
    'all':       [host1, host2, host3, host4],
    'openstack': [host1],
    'cfgm':      [host1],
    'control':   [host1, host2],
    'compute':   [host3, host4],
    'collector': [host1, host2],
    'webui':     [host1],
    'database':  [host1, host2],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a3s14', 'a3s15', 'a3s16','a3s18']
}

env.password = 'c0ntrail123'

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',

    host_build: 'c0ntrail123',
}
