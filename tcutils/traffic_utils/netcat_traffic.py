# traffic generator using nc.traditional, supports only tcp and udp protocol

from tcutils.util import retry
from time import sleep

default_data = '*****This is default data.*****'
result_file = '/tmp/nc.result'


def start_nc(
        self,
        sender_vm_fix,
        receiver_vm_fix,
        proto,
        sport,
        dport,
        pkt_count=1):

    result, pid_recv = start_nc_receiver(self, receiver_vm_fix, proto, dport)
    assert result, "netcat could not start on receiver"
    sleep(1)
    result, sent = start_nc_sender(
        self, sender_vm_fix, receiver_vm_fix, proto,
        sport, dport, data=default_data, pkt_count=pkt_count)
    assert result, "netcat could not start on sender"

    return sent, pid_recv


def stop_nc(self, vm_fix, pid):

    if pid:
        cmd = 'kill -s SIGINT %s' % pid
        output = vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        self.logger.debug("output to kill netcat on VM: %s" % output)


def get_packet_count_nc(self, vm_fix):

    cmd = 'cat %s' % result_file
    output = vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
    self.logger.debug("output for count: %s" % output)

    if 'rcvd' in output[cmd]:
        recv = output[cmd].split('rcvd ')[1].split('\r')[0]
    else:
        recv = 0

    if 'sent' in output[cmd]:
        sent = output[cmd].split('sent ')[1].split(',')[0]
    else:
        sent = 0

    return (int(sent), int(recv))


@retry(delay=3, tries=3)
def start_nc_receiver(self, receiver_vm_fix, proto, dport):

    pid_recv = None
    result = False
    if proto == 'udp':
        cmd = 'nc.traditional -l -s %s -p %s -u -vv 2>%s 1>%s' % (
            receiver_vm_fix.vm_ip, dport, result_file, result_file)
    elif proto == 'tcp':
        cmd = 'nc.traditional -l -s %s -p %s -vv 2>%s 1>%s' % (
            receiver_vm_fix.vm_ip, dport, result_file, result_file)
    output = receiver_vm_fix.run_cmd_on_vm(
        cmds=[cmd],
        as_sudo=True,
        as_daemon=True)
    self.logger.debug("output for starting nc on recvr: %s" % output[cmd])

    cmd = 'pidof nc.traditional'
    output = receiver_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
    self.logger.debug("output for cmd %s: %s" % (cmd, output[cmd]))
    if 'received nonzero return code 1 while executing' in output[cmd]:
        self.logger.warn(
            "nc.traditional could not start properly on receiver, retrying after 3 second")
        result = False
        return result, pid_recv

    if '\r\n' in output[cmd]:
        pid_recv = output[cmd].split('\r\n')[1].split('\r')[0]
        result = True
    else:
        result = False

    return result, pid_recv


@retry(delay=3, tries=3)
def start_nc_sender(
        self,
        sender_vm_fix,
        receiver_vm_fix,
        proto,
        sport,
        dport,
        data=default_data,
        pkt_count=1):

    if not pkt_count:
        pkt_count = 1
    pid_sender = None
    sent = 0
    result = False
    if proto == 'udp':
        cmd1 = 'echo -e "%s" | nc.traditional %s %s -s %s -p %s -u -vv 2>%s 1>%s' % (
            data, receiver_vm_fix.vm_ip, dport, sender_vm_fix.vm_ip, sport, result_file, result_file)
    elif proto == 'tcp':
        cmd1 = 'echo -e "%s" | nc.traditional %s %s -s %s -p %s -vv 2>%s 1>%s' % (
            data, receiver_vm_fix.vm_ip, dport, sender_vm_fix.vm_ip, sport, result_file, result_file)

    for i in xrange(pkt_count):
        output = sender_vm_fix.run_cmd_on_vm(
            cmds=[cmd1],
            as_sudo=True,
            as_daemon=True)
        sleep(0.5)
        cmd = 'pidof nc.traditional'
        output = sender_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        self.logger.debug("output for cmd %s: %s" % (cmd, output[cmd]))
        if 'received nonzero return code 1 while executing' in output[cmd]:
            self.logger.warn(
                "nc.traditional could not start properly on sender, retrying after 3 seconds")
            result = False
            return result, sent

        if '\r\n' in output[cmd]:
            pid_sender = output[cmd].split('\r\n')[1].split('\r')[0]
            result = True
            cmd = 'kill -s SIGINT %s' % pid_sender
            output = sender_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
            self.logger.debug("output to kill on sender : %s" % output)
            sent1, recv1 = get_packet_count_nc(self, sender_vm_fix)
            sent = sent + sent1
        else:
            result = False
        sleep(0.5)

    return result, sent
