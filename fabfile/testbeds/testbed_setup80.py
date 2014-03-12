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
host36 = 'root@10.84.23.6'
host37 = 'root@10.84.23.7'
host38 = 'root@10.84.23.8'
host39 = 'root@10.84.23.9'
host40 = 'root@10.84.23.10'

host41 = 'root@10.84.21.34'
host42 = 'root@10.84.21.35'
host43 = 'root@10.84.21.36'
host44 = 'root@10.84.21.37'
host45 = 'root@10.84.21.38'
host46 = 'root@10.84.21.39'
host47 = 'root@10.84.21.40'
host48 = 'root@10.84.21.41'
host49 = 'root@10.84.21.42'
host50 = 'root@10.84.21.43'
host51 = 'root@10.84.22.1'
host52 = 'root@10.84.22.2'
host53 = 'root@10.84.22.3'
host54 = 'root@10.84.22.4'
host55 = 'root@10.84.22.5'
host56 = 'root@10.84.22.6'
host57 = 'root@10.84.22.7'
host58 = 'root@10.84.22.8'
host59 = 'root@10.84.22.9'
host60 = 'root@10.84.22.10'
host61 = 'root@10.84.22.11'
host62 = 'root@10.84.22.12'
host63 = 'root@10.84.22.13'
host64 = 'root@10.84.22.14'
host65 = 'root@10.84.22.15'
host66 = 'root@10.84.22.16'
host67 = 'root@10.84.22.17'
host68 = 'root@10.84.22.18'
host69 = 'root@10.84.22.19'
host70 = 'root@10.84.22.20'
host71 = 'root@10.84.23.11'
host72 = 'root@10.84.23.12'
host73 = 'root@10.84.23.13'
host74 = 'root@10.84.23.14'
host75 = 'root@10.84.23.15'
host76 = 'root@10.84.23.16'
host77 = 'root@10.84.23.17'
host78 = 'root@10.84.23.18'
host79 = 'root@10.84.23.19'
host80 = 'root@10.84.23.20'

ext_routers = [('mx1', '10.84.23.253'), ('mx2', '10.84.23.252')]
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = "10.84.46.0/24"

host_build = 'ajayhn@10.84.5.101'

env.roledefs = {
    'all': [host1, host2, host3, host4, host5, host6, host7, host8, host9, host10,
            host11, host12, host13, host14, host15, host16, host17, host18, host19, host20,
            host21, host22, host23, host24, host25, host26, host27, host28, host29, host30,
            host31, host32, host33, host34, host35, host36, host37, host38, host39, host40,
            host41, host42, host43, host44, host45, host46, host47, host48, host49, host50,
            host51, host52, host53, host54, host55, host56, host57, host58, host59, host60,
            host61, host62, host63, host64, host65, host66, host67, host68, host69, host70,
            host71, host72, host73, host74, host75, host76, host77, host78, host79, host80],
    'cfgm': [host40],
    'control': [host1, host2],
    'compute': [host3, host4, host5, host6, host7, host8, host9, host10,
            host11, host12, host13, host14, host15, host16, host17, host18, host19, host20,
            host21, host22, host23, host24, host25, host26, host27, host28, host29, host30,
            host31, host32, host33, host34, host35, host36, host37, host38, host39,
            host41, host42, host43, host44, host45, host46, host47, host48, host49, host50,
            host51, host52, host53, host54, host55, host56, host57, host58, host59, host60,
            host61, host62, host63, host64, host65, host66, host67, host68, host69, host70,
            host71, host72, host73, host74, host75, host76, host77, host78, host79, host80],
    'database': [host39, host38],
    'collector': [host37, host36],
    'webui': [host35],
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
'b3s6', 
'b3s7', 
'b3s8', 
'b3s9', 
'b3s10',
'b1s34', 
'b1s35', 
'b1s36', 
'b1s37', 
'b1s38', 
'b1s39', 
'b1s40',
'b1s41', 
'b1s42', 
'b1s43', 
'b2s1', 
'b2s2', 
'b2s3', 
'b2s4', 
'b2s5', 
'b2s6', 
'b2s7', 
'b2s8', 
'b2s9', 
'b2s10',
'b2s11', 
'b2s12', 
'b2s13', 
'b2s14', 
'b2s15', 
'b2s16', 
'b2s17', 
'b2s18', 
'b2s19', 
'b2s20',
'b3s11', 
'b3s12', 
'b3s13', 
'b3s14', 
'b3s15', 
'b3s16', 
'b3s17', 
'b3s18', 
'b3s19', 
'b3s20', 
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
    host36: 'c0ntrail123',
    host37: 'c0ntrail123',
    host38: 'c0ntrail123',
    host39: 'c0ntrail123',
    host40: 'c0ntrail123',
    host41: 'c0ntrail123',
    host42: 'c0ntrail123',
    host43: 'c0ntrail123',
    host44: 'c0ntrail123',
    host45: 'c0ntrail123',
    host46: 'c0ntrail123',
    host47: 'c0ntrail123',
    host48: 'c0ntrail123',
    host49: 'c0ntrail123',
    host50: 'c0ntrail123',
    host51: 'c0ntrail123',
    host52: 'c0ntrail123',
    host53: 'c0ntrail123',
    host54: 'c0ntrail123',
    host55: 'c0ntrail123',
    host56: 'c0ntrail123',
    host57: 'c0ntrail123',
    host58: 'c0ntrail123',
    host59: 'c0ntrail123',
    host60: 'c0ntrail123',
    host61: 'c0ntrail123',
    host62: 'c0ntrail123',
    host63: 'c0ntrail123',
    host64: 'c0ntrail123',
    host65: 'c0ntrail123',
    host66: 'c0ntrail123',
    host67: 'c0ntrail123',
    host68: 'c0ntrail123',
    host69: 'c0ntrail123',
    host70: 'c0ntrail123',
    host71: 'c0ntrail123',
    host72: 'c0ntrail123',
    host73: 'c0ntrail123',
    host74: 'c0ntrail123',
    host75: 'c0ntrail123',
    host76: 'c0ntrail123',
    host77: 'c0ntrail123',
    host78: 'c0ntrail123',
    host79: 'c0ntrail123',
    host80: 'c0ntrail123',

    host_build: 'c0ntrail123'
}
