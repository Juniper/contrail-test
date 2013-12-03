from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1 = 'root@10.204.216.48'
host2 = 'root@10.204.216.42'
host3 = 'root@10.204.216.40'
host4 = 'root@10.204.216.33'
host5 = 'root@10.204.216.5'
host6 = 'root@10.204.216.12'
host7 = 'root@10.204.216.37'
host8 = 'root@10.204.217.16'

ext_routers = [('mx1', '10.204.216.253')]
router_asn = 64512
public_vn_rtgt = 10003
public_vn_subnet = '10.204.219.56/29'

host_build = 'root@10.204.216.4'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5, host6, host7, host8],
    'cfgm': [host1],
    'openstack': [host6],
    'webui': [host7],
    'control': [host4, host3],
    'compute': [host2, host5],
    'collector': [host2, host3],
    'database': [host8],
    'build': [host_build],
}

env.hostnames = {
    'all': ['nodea10', 'nodea4', 'nodea2', 'nodeb2', 'nodeb12','nodea16','nodeb6','nodec31']
}

bond= {
    host2 : { 'name': 'bond0', 'member': ['p2p0p0','p2p0p1','p2p0p2','p2p0p3'], 'mode':'balance-xor' },
    host5 : { 'name': 'bond0', 'member': ['p4p0p0','p4p0p1','p4p0p2','p4p0p3'], 'mode':'balance-xor' },
}

control = {
    host1 : { 'ip': '192.168.10.1/24', 'gw' : '192.168.10.254', 'device':'eth0' },
    host2 : { 'ip': '192.168.10.2/24', 'gw' : '192.168.10.254', 'device':'p0p25p0' },
    host3 : { 'ip': '192.168.10.3/24', 'gw' : '192.168.10.254', 'device':'eth0' },
    host4 : { 'ip': '192.168.10.4/24', 'gw' : '192.168.10.254', 'device':'eth3' },
    host5 : { 'ip': '192.168.10.5/24', 'gw' : '192.168.10.254', 'device':'p6p0p1' },
    host6 : { 'ip': '192.168.10.6/24', 'gw' : '192.168.10.254', 'device':'eth0' },
    host7 : { 'ip': '192.168.10.7/24', 'gw' : '192.168.10.254', 'device':'eth1' },
    host8 : { 'ip': '192.168.10.8/24', 'gw' : '192.168.10.254', 'device':'eth1' },
}

data = {
    host2 : { 'ip': '192.161.10.1/24', 'gw' : '192.161.10.254', 'device':'bond0' },
    host5 : { 'ip': '192.161.10.2/24', 'gw' : '192.161.10.254', 'device':'bond0' },
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',
    host4: 'c0ntrail123',
    host5: 'c0ntrail123',
    host6: 'c0ntrail123',
    host7: 'c0ntrail123',
    host8: 'c0ntrail123',

    host_build: 'c0ntrail123',
}

env.test_repo_dir='/homes/chhandak/test'
env.mail_from='chhandak@juniper.net'
env.mail_to='chhandak@juniper.net'
env.log_scenario='Multiple Interface CentOS Sanity'
env.interface_rename = True

