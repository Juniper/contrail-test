import paramiko
from netaddr import *

from fabfile.config import testbed

def hstr_to_ip(host_string):
    return host_string.split('@')[1]

def get_control_host_string(mgmt_host):
    isPresent= getattr(testbed, 'control', None)
    if isPresent:
        host_ip=getattr(testbed, 'control', None)[mgmt_host]['ip']
        ip = str(IPNetwork(host_ip).ip)
        user= mgmt_host.split('@')[0]
        host_details= user+'@'+ip
    else :
        host_details= mgmt_host
    return host_details

def get_service_token():
    svc_opt = ''
    testbed.service_token = getattr(testbed, 'service_token', '')
    if testbed.service_token:
        svc_opt = '--service_token %s' % (testbed.service_token)
    return svc_opt

def get_haproxy_opt():
    testbed.haproxy = getattr(testbed, 'haproxy', False)
    haproxy_opt = '--haproxy' if testbed.haproxy else ''
    return haproxy_opt

def verify_sshd(host, user, password):
    try:
        client = paramiko.Transport((host, 22))
        client.connect(username=user, password=password)
    except Exception:
        return False

    client.close()
    return True
