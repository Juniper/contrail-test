from fabric.api import env

os_username = 'admin'
os_password = 'contrail123'
os_tenant_name = 'demo'

host1  = 'root@10.84.21.1'
host2  = 'root@10.84.21.2'
host3  = 'root@10.84.21.3'
host4  = 'root@10.84.21.4'
host5  = 'root@10.84.21.5'
host6  = 'root@10.84.21.6'
host7  = 'root@10.84.21.7'
host8  = 'root@10.84.21.8'
host9  = 'root@10.84.21.9'
host10 = 'root@10.84.21.10'
host11 = 'root@10.84.21.11'
host12 = 'root@10.84.21.12'
host13 = 'root@10.84.21.13'
host14 = 'root@10.84.21.14'
host15 = 'root@10.84.21.15'
host16 = 'root@10.84.21.16'
host17 = 'root@10.84.21.17'
host18 = 'root@10.84.21.18'
host19 = 'root@10.84.21.19'
host20 = 'root@10.84.21.20'
host21 = 'root@10.84.21.21'
host22 = 'root@10.84.21.22'
host23 = 'root@10.84.21.23'
host24 = 'root@10.84.21.24'
host25 = 'root@10.84.21.28'
host26 = 'root@10.84.21.29'
host27 = 'root@10.84.21.30'
host28 = 'root@10.84.21.31'
host29 = 'root@10.84.21.32'
host30 = 'root@10.84.21.33'
host31 = 'root@10.84.23.1'
host32 = 'root@10.84.23.2'
host33 = 'root@10.84.23.3'
host34 = 'root@10.84.23.4'
host35 = 'root@10.84.23.5'
#host36 = 'root@10.84.23.6'
host37 = 'root@10.84.23.7'
host38 = 'root@10.84.23.8'
host39 = 'root@10.84.23.9'
host40 = 'root@10.84.23.10'

ext_routers = [('mx1', '10.84.23.253'), ('mx2', '10.84.23.252')]
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.46.0/24"

host_build = 'ajayhn@10.84.5.101'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5, host6, host7, host8, host9, host10,
            host11, host12, host13, host14, host15, host16, host17, host18, host19, host20,
            host21, host22, host23, host24, host25, host26, host27, host28, host29, host30,
            host31, host32, host33, host34, host35, 
            #host36, 
            host37, host38, host39, host40],
    'cfgm': [host40],
    'control': [host1, host2],
    'compute': [host3, host4, host5, host6, host7, host8, host9, host10,
            host11, host12, host13, host14, host15, host16, host17, host18, host19, host20,
            host21, host22, host23, host24, host25, host26, host27, host28, host29, host30,
            host31, host32, host33, host34, host35, 
            #host36,
            host37, host38, host39],
    'collector': [host40],
    'webui': [host40],
    'database': [host40],
    'build': [host_build],
}

env.hostnames = {
    'all': [
'b1s1', 
'b1s2', 
'b1s3', 
'b1s4', 
'b1s5', 
'b1s6', 
'b1s7', 
'b1s8', 
'b1s9', 
'b1s10',
'b1s11', 
'b1s12', 
'b1s13', 
'b1s14', 
'b1s15', 
'b1s16', 
'b1s17', 
'b1s18', 
'b1s19', 
'b1s20',
'b1s21', 
'b1s22', 
'b1s23', 
'b1s24', 
'b1s28', 
'b1s29', 
'b1s30', 
'b1s31', 
'b1s32', 
'b1s33',
'b3s1', 
'b3s2', 
'b3s3', 
'b3s4', 
'b3s5', 
#'b3s6', 
'b3s7', 
'b3s8', 
'b3s9', 
'b3s10'
]
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
    host9: 'c0ntrail123',
    host10: 'c0ntrail123',
    host11: 'c0ntrail123',
    host12: 'c0ntrail123',
    host13: 'c0ntrail123',
    host14: 'c0ntrail123',
    host15: 'c0ntrail123',
    host16: 'c0ntrail123',
    host17: 'c0ntrail123',
    host18: 'c0ntrail123',
    host19: 'c0ntrail123',
    host20: 'c0ntrail123',
    host21: 'c0ntrail123',
    host22: 'c0ntrail123',
    host23: 'c0ntrail123',
    host24: 'c0ntrail123',
    host25: 'c0ntrail123',
    host26: 'c0ntrail123',
    host27: 'c0ntrail123',
    host28: 'c0ntrail123',
    host29: 'c0ntrail123',
    host30: 'c0ntrail123',
    host31: 'c0ntrail123',
    host32: 'c0ntrail123',
    host33: 'c0ntrail123',
    host34: 'c0ntrail123',
    host35: 'c0ntrail123',
    #host36: 'c0ntrail123',
    host37: 'c0ntrail123',
    host38: 'c0ntrail123',
    host39: 'c0ntrail123',
    host40: 'c0ntrail123',

    host_build: 'c0ntrail123'
}
