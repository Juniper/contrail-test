from builtins import object
import re
import os
import sys
from tcutils.util import get_random_name
from vm_test import VMFixture
from bms_fixture import BMSFixture
dir_path = os.path.dirname(os.path.realpath(__file__))
TCPSERVER = dir_path+'/../tcpechoserver.py'
TCPCLIENT = dir_path+'/../tcpechoclient.py'
UDPSERVER = dir_path+'/../udpechoserver.py'
UDPCLIENT = dir_path+'/../udpechoclient.py'

class SocketTrafficUtil(object):

    def __init__(self):
        self.client_sent = None
        self.client_recv = None
        self.server_sent = None
        self.server_recv = None
        random_name = get_random_name()
        self.client_pid_file = '/tmp/client-%s.pid'%random_name
        self.client_stats_file = '/tmp/client-%s.stats'%random_name
        self.client_log_file = '/tmp/client-%s.log'%random_name
        self.server_pid_file = '/tmp/server-%s.pid'%random_name
        self.server_stats_file = '/tmp/server-%s.stats'%random_name
        self.server_log_file = '/tmp/server-%s.log'%random_name

    def start(self, sender, receiver, proto, sport, dport,
              count=0, fip=None, sender_vn_fqname=None,
              receiver_vn_fqname=None, af=None, slow=False):
        self.client = sender
        self.server = receiver
        if proto.lower() == 'tcp':
            self.server_script = TCPSERVER
            self.client_script = TCPCLIENT
        elif proto.lower() == 'udp':
            self.server_script = UDPSERVER
            self.client_script = UDPCLIENT
        else:
            raise Exception('Unsupported proto %s'%proto)
        self.proto = proto
        self.sport = sport
        self.dport = dport
        self.logger = self.client.inputs.logger
        self.count = count
        self.slow = slow
        if isinstance(self.client,VMFixture):
            self.src_ip = self.client.get_vm_ips(
                vn_fq_name=sender_vn_fqname, af=af)[0]
        else:
            self.src_ip = self.client.get_bms_ips()[0]

        if isinstance(self.server,VMFixture):
            self.dst_ip = fip if fip else self.server.get_vm_ips(
                vn_fq_name=receiver_vn_fqname, af=af)[0]
        else:
            self.dst_ip = self.server.get_bms_ips()[0]
        assert self.start_server(), 'Unable to start server'
        assert self.start_client(), 'Unanle to start client'
        return True

    def start_server(self):
        cmd = '--start_port %s --end_port %s --pid_file %s --stats_file %s'%(
            self.dport, self.dport, self.server_pid_file,
            self.server_stats_file)
        cmd = 'python /tmp/%s %s'%(os.path.basename(self.server_script), cmd)
        if isinstance(self.server,VMFixture):
            cmd = cmd + ' 0<&- &> %s'%self.server_log_file
            self.server.copy_file_to_vm(self.server_script, '/tmp/')
            self.server.run_cmd_on_vm(cmds=[cmd], as_sudo=True, as_daemon=True)
        else:
            cmd = cmd + ' >& %s &'%self.server_log_file
            self.server.copy_file_to_bms(self.server_script, '/tmp/')
            self.server.run_namespace(cmd, pty=False)
        return True

    def start_client(self):
        slow = '--slow' if self.slow else ''
        sport = '--sport %s'%self.sport if self.sport else ''
        count = '--count %s'%self.count if self.count else ''
        cmd = '--servers %s %s --dports %s --retry %s %s --pid_file %s'\
              ' --stats_file %s'%(self.dst_ip, sport,
              self.dport, count, slow, self.client_pid_file,
              self.client_stats_file)
        cmd = 'python /tmp/%s %s'%(os.path.basename(self.client_script), cmd)
        if isinstance(self.client,VMFixture):
            cmd = cmd + ' 0<&- &> %s'%self.client_log_file
            self.client.copy_file_to_vm(self.client_script, '/tmp/')
            self.client.run_cmd_on_vm(cmds=[cmd], as_sudo=True, as_daemon=True)
        else:
            cmd = cmd + ' >& %s &'%self.client_log_file
            self.client.copy_file_to_bms(self.client_script, '/tmp/')
            self.client.run_namespace(cmd, pty=False)
        return True

    def stop(self):
        return self.get_packet_count(poll=False)

    def get_stats(self, vm, pid_file, stats_file, poll=True):
        signal = ''
        if poll is True:
            signal = '-USR1'
        cmd = 'kill %s $(cat %s); sync; cat %s'%(signal, pid_file, stats_file)
        if isinstance(vm,VMFixture):
                output = vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
                pattern = 'dport: (?P<dport>\d+) -.* ip: (?P<ip>.*) - ' \
                        + 'sent: (?P<sent>\d+) - recv: (?P<recv>\d+)'
                return [m.groupdict() for m in re.finditer(pattern, output[cmd] or '')]
        else:
                cmd = vm.run_namespace(cmd)
                pattern = 'dport: (?P<dport>\d+) -.* ip: (?P<ip>.*) - ' \
                        + 'sent: (?P<sent>\d+) - recv: (?P<recv>\d+)'
                return [m.groupdict() for m in re.finditer(pattern, cmd or '')]

    def get_packet_count(self, dport=None, poll=True):
        client_stats = self.get_stats(self.client,
            self.client_pid_file, self.client_stats_file, poll=poll)
        server_stats = self.get_stats(self.server,
            self.server_pid_file, self.server_stats_file, poll=poll)
        self.client_sent = sum([int(d['sent']) for d in client_stats])
        self.server_sent = sum([int(d['sent']) for d in server_stats])
        self.client_recv = sum([int(d['recv']) for d in client_stats])
        self.server_recv = sum([int(d['recv']) for d in server_stats])
        self.logger.info("Client - Sent: %s, Received: %s" %(
            self.client_sent, self.client_recv))
        self.logger.info("Server - Sent: %s, Received: %s" %(
            self.server_sent, self.server_recv))
        return (self.client_sent, self.client_recv,
                self.server_sent, self.server_recv)

    def poll(self):
        return self.get_packet_count(poll=True)
