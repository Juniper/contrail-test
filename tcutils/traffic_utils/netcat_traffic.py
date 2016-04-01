# traffic generator using nc.traditional, supports only tcp and udp protocol

from tcutils.util import retry
from base_traffic import * 
from tcutils.util import get_random_name
default_data = '*****This is default data.*****'
result_file = '/tmp/nc'

class Netcat(BaseTraffic):

    def __init__(self):

        self.sender_pid = None
        self.receiver_pid = None
        self.sent = None
        self.recv = None
        self.result_file = result_file + '_' + get_random_name() + '.result'

    def start(
            self,
            sender_vm_fix,
            receiver_vm_fix,
            proto,
            sport,
            dport):

        self.sender_vm_fix = sender_vm_fix
        self.receiver_vm_fix = receiver_vm_fix
        self.proto = proto
        self.sport = sport
        self.dport = dport
        self.inputs = sender_vm_fix.inputs
        self.logger = self.inputs.logger
        self.logger.info('Starting netcat session from %s to %s,'
            'Protocol : %s, Source port : %s, Dest port : %s' % (
            sender_vm_fix.vm_ip, receiver_vm_fix.vm_ip,
            proto, sport, dport))

        result, self.receiver_pid = self.start_nc_receiver()
        if not result or not self.receiver_pid:
            self.logger.error("Netcat could not start on receiver")
            return False
        sleep(1)
        result, self.sender_pid = self.start_nc_sender()
        if not result or not self.sender_pid:
            self.logger.error("Netcat could not start on sender")
            return False

        return True
    # end start

    def stop(self):
        if self.receiver_pid:
            cmd = 'kill -s SIGINT %s' % self.receiver_pid
            output = self.receiver_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
            self.logger.debug("Result of killing netcat on VM: %s" % output)

        self.sent = self.get_sender_packet_count()
        self.recv = self.get_packet_count()
        self.logger.info("Stopped netcat session from %s to %s, "
            "Sent : %s, Received: %s" % (self.sender_vm_fix.vm_ip,
            self.receiver_vm_fix.vm_ip, self.sent, self.recv))
        return (self.sent, self.recv)

    def get_sender_packet_count(self):
        sent = 0
        if self.sender_pid:
            cmd = 'kill -s SIGINT %s' % self.sender_pid
            output = self.sender_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
            self.logger.debug("Output to kill on sender : %s" % output)
            sent1, recv1 = self.get_packet_count_nc(self.sender_vm_fix)
            sent = sent + sent1
        return sent

    def get_packet_count(self):

        sent, self.recv = self.get_packet_count_nc(self.receiver_vm_fix) 
        return self.recv

    def get_packet_count_nc(self, vm_fix):

        cmd = 'cat %s' % self.result_file
        output = vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        self.logger.debug("Output for count: %s" % output)

        if 'rcvd' in output[cmd]:
            recv = output[cmd].split('rcvd ')[1].split('\r')[0]
        else:
            recv = 0
        if 'sent' in output[cmd]:
            sent = output[cmd].split('sent ')[1].split(',')[0]
        else:
            sent = 0

        return (int(sent), int(recv))
    # end get_packet_count_nc

    @retry(delay=3, tries=3)
    def start_nc_receiver(self):

        pid_recv = None
        result = False
        if self.proto == 'udp':
            cmd = 'nc.traditional -l -s %s -p %s -u -vv 2>%s 1>%s' % (
                self.receiver_vm_fix.vm_ip, self.dport, self.result_file, self.result_file)
        elif self.proto == 'tcp':
            cmd = 'nc.traditional -l -s %s -p %s -vv 2>%s 1>%s' % (
                self.receiver_vm_fix.vm_ip, self.dport, self.result_file, self.result_file)
        output = self.receiver_vm_fix.run_cmd_on_vm(
            cmds=[cmd],
            as_sudo=True,
            as_daemon=True)
        self.logger.debug("output for starting nc on recvr: %s" % output[cmd])

        cmd = 'pidof nc.traditional'
        output = self.receiver_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        self.logger.debug("output for cmd %s: %s" % (cmd, output[cmd]))
        if 'received nonzero return code 1 while executing' in output[cmd]:
            self.logger.warn(
                "nc.traditional could not start properly on receiver, retrying after 3 second")
            result = False
            return result, pid_recv

        if '\r\n' in output[cmd]:
            pid_recv = output[cmd].split('\r\n')[1].split('\r')[0]
            result = True
        elif '\r' in output[cmd]:
            pid_recv = output[cmd].split('\r')[0]
            result = True
        else:
            result = False

        return result, pid_recv
    # end start_nc_receiver


    @retry(delay=3, tries=3)
    def start_nc_sender(
            self,
            data=default_data):

        sender_pid = None
        sent = 0
        result = False

        if self.proto == 'udp':
            cmd1 = 'echo -e "%s" | nc.traditional %s %s -s %s -p %s -u -vv 2>%s 1>%s' % (
                data, self.receiver_vm_fix.vm_ip, self.dport, self.sender_vm_fix.vm_ip, self.sport, self.result_file, self.result_file)
        elif self.proto == 'tcp':
            cmd1 = 'echo -e "%s" | nc.traditional %s %s -s %s -p %s -vv 2>%s 1>%s' % (
                data, self.receiver_vm_fix.vm_ip, self.dport, self.sender_vm_fix.vm_ip, self.sport, self.result_file, self.result_file)

        output = self.sender_vm_fix.run_cmd_on_vm(
            cmds=[cmd1],
            as_sudo=True,
            as_daemon=True)
        sleep(0.5)
        cmd = 'pidof nc.traditional'
        output = self.sender_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        self.logger.debug("output for cmd %s: %s" % (cmd, output[cmd]))
        if 'received nonzero return code 1 while executing' in output[cmd]:
            self.logger.warn(
                "nc.traditional could not start properly on sender, retrying after 3 seconds")
            result = False
            return result, sent

        if '\r\n' in output[cmd]:
            sender_pid = output[cmd].split('\r\n')[1].split('\r')[0]
            result = True
        elif '\r' in output[cmd]:
            sender_pid = output[cmd].split('\r')[0]
            result = True
        else:
            result = False

        return result, sender_pid
    # end start_nc_sender
