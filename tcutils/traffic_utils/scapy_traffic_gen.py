import logging as LOG

from collections import OrderedDict
from tcutils.util import get_random_name, retry
from string import Template
class ScapyTraffic:
    '''
    This class help us to create and send scapy traffic from a VM.
    
    Configurable values through scapy:
    For Ether Header (Ether):
    <Dot3  dst=ff:ff:ff:ff:ff:ff src=00:00:00:00:00:00 type=0x800 |>
    
    For Dot1Q Header:
    <Dot1Q  prio=0L id=0L vlan=1L type=0x0 |>
    
    For IPv4 Header:
    <IP  version=4L ihl=5L tos=0x0 len=20 id=1 flags= frag=0L ttl=64 
    proto=ip chksum=0x7ce7 src=127.0.0.1 dst=127.0.0.1 |>
    
    For IPv6 Header:
    <IPv6  version=6L tc=0L fl=0L plen=0 nh=No Next Header hlim=64 src=::1 dst=::1 |>
    
    For TCP Header:
    <TCP  sport=ftp_data dport=http seq=0 ack=0 dataofs=5L reserved=0L
    flags=S window=8192 chksum=0x0 urgptr=0 |>
    
    For UDP Header:
    <UDP  sport=domain dport=domain len=8 chksum=0x0 |>
    
    Usage:
    scapy_obj = ScapyTraffic(src_vm_fixture, "eth0", 1, 100, 
                            ether = {'src':'00:11:22:33:44:55',
                                      'dst': '00:11:22:33:44:55',
                                      'type': 0x800},
                            ip = {'src':'1.1.1.1',
                                   'dst': '2.2.2.2',
                                   'proto':'tcp',
                                   'tos':0x14})
    scapy_command = scapy_obj.scapy_send_stream_cmd()
    '''

    def __init__(self, src_vm_fixture, interface=None, interval=1, count=1, **kwargs):
        self.src_vm_fixture = src_vm_fixture
        self.interface = interface or self.src_vm_fixture.get_vm_interface_name()
        self.interval = interval
        self.count = count
        self.params = OrderedDict()
        self.params['Ether'] = kwargs.get('ether',{})
        self.params['Dot1Q'] = kwargs.get('dot1q',{})
        self.params['IP'] = kwargs.get('ip',{})
        self.params['IPv6'] = kwargs.get('ipv6',{})
        self.params['TCP'] = kwargs.get('tcp',{})
        self.params['UDP'] = kwargs.get('udp',{})
        self.payload = kwargs.get('payload',
                        "'ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ'")
        self.pid_file = '/tmp/scapy_%s.pid' % (get_random_name())

    def scapy_build_stream(self):
        stream = ''
        if self.params['TCP'] and self.params['UDP']:
            self.logger.error("Both TCP and UDP parameters cannot be"
                              " set in a single stream")
            return
        if self.params['IP'] and self.params['IPv6']:
            self.logger.error("Both IPv4 and IPv6 parameters cannot be"
                              " set in a single stream")
            return
        for header,dict_values in self.params.iteritems():
            if dict_values:
                vars = []
                for key,value in dict_values.iteritems():
                    if type(value) is str:
                        var = "%s='%s'" % (key,value)
                    else:
                        var = "%s=%d" % (key,value)
                    vars.append(var)
                header_fields = ','.join(vars)
                stream = stream + "%s(" % header + header_fields +')/'
        stream = stream+"payload"
        return stream
    # end scapy_build_stream

    def start(self):
        stream = self.scapy_build_stream()
        cmd = "sendp(%s,iface='%s',inter=%f,count=%d)" %\
                            (stream, self.interface,
                            self.interval, self.count)
        python_code = Template('''
from scapy.all import *
payload = $data
$scapy_cmd''')
        code = python_code.substitute(data = self.payload,
                                             scapy_cmd = cmd)
        self.src_vm_fixture.run_python_code(code, 
                                            pidfile= self.pid_file,
                                            as_daemon = True)
        return cmd
    # end start
    
    def stop(self):
        cmd = 'cat %s | xargs kill ' % (self.pid_file)
        self.src_vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
    # end stop

if __name__ == "__main__":
    scapy_obj = ScapyTraffic(src_vm_fixture, "eth0", 1, 100, 
                            ether = {'src':'00:11:22:33:44:55',
                                      'dst': '00:11:22:33:44:55',
                                      'type': 0x800},
                            ip = {'src':'1.1.1.1',
                                   'dst': '2.2.2.2',
                                   'proto':'tcp',
                                   'tos':0x14}
                            )
    pkt_stream = scapy_obj.scapy_build_stream()
    print pkt_stream
