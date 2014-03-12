from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.84.23.34'
host2 = 'root@10.84.23.35'
host3 = 'root@10.84.23.36'
host4 = 'root@10.84.23.37'
host5 = 'root@10.84.23.38'
host6 = 'root@10.84.23.39'
host7 = 'root@10.84.23.40'

ext_routers = [('b3-mx1', '10.84.20.252'), ('b3-mx2', '10.84.20.253')]
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.49.0/24"

host_build = 'ajayhn@10.84.5.101'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5, host6, host7],
    'cfgm': [host7],
    'openstack': [host7],
    'control': [host6, host7],
    'compute': [host1, host2, host3, host4, host5],
    'collector': [host7],
    'database': [host7],
    'webui': [host7],
    'build': [host_build],
}

env.hostnames = {
    'all': ['b3s34', 'b3s35', 'b3s36','b3s37', 'b3s38', 'b3s39', 'b3s40']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',
    host5: 'c0ntrail123',
    host6: 'c0ntrail123',
    host7: 'c0ntrail123',

    host_build: 'c0ntrail123',
}



control = {
    host1 : { 'ip': '10.84.20.34/24', 'gw' : '10.84.20.254', 'device' : 'p4p0p0'},
    host2 : { 'ip': '10.84.20.35/24', 'gw' : '10.84.20.254', 'device' : 'p4p0p0'},
    host3 : { 'ip': '10.84.20.36/24', 'gw' : '10.84.20.254', 'device' : 'p4p0p0'},
    host4 : { 'ip': '10.84.20.37/24', 'gw' : '10.84.20.254', 'device' : 'p4p0p0'},
    host5 : { 'ip': '10.84.20.38/24', 'gw' : '10.84.20.254', 'device' : 'p4p0p0'},
    host6 : { 'ip': '10.84.20.39/24', 'gw' : '10.84.20.254', 'device' : 'eth0'},
    host7 : { 'ip': '10.84.20.40/24', 'gw' : '10.84.20.254', 'device' : 'eth0'},
}

data = {
    host1 : { 'ip': '10.84.20.34/24', 'gw' : '10.84.20.254', 'device' : 'p4p0p0'},
    host2 : { 'ip': '10.84.20.35/24', 'gw' : '10.84.20.254', 'device' : 'p4p0p0'},
    host3 : { 'ip': '10.84.20.36/24', 'gw' : '10.84.20.254', 'device' : 'p4p0p0'},
    host4 : { 'ip': '10.84.20.37/24', 'gw' : '10.84.20.254', 'device' : 'p4p0p0'},
    host5 : { 'ip': '10.84.20.38/24', 'gw' : '10.84.20.254', 'device' : 'p4p0p0'},
}
