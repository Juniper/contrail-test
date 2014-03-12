from fabric.api import env

host1 = 'root@10.84.7.8'
host2 = 'root@10.84.7.18'
host3 = 'root@10.84.9.44'
host4 = 'root@10.84.9.45'
host5 = 'root@10.84.13.2'
host6 = 'root@10.84.13.3'
host7 = 'root@10.84.13.16'
host8 = 'root@10.84.13.34'
host9 = 'root@10.84.13.39'
#host10 = 'root@10.84.13.42'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = '1.1.1.0/24'

host_build = 'ajayhn@10.84.5.101'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5, host6, host7, host8, host9],
    'cfgm': [host1],
    'control': [host2, host3],
    'compute': [host4, host5, host6, host7, host8, host9],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
}

env.hostnames = {
    'all': ['a2s8', 'a2s18', 'a3s44','a3s45', 'a6s2', 'a6s3', 'a6s16', 'a6s34', 'a6s39', 'a6s42']
}
