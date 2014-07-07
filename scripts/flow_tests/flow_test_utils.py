from time import sleep

from servicechain.config import ConfigSvcChain
from tcutils.commands import ssh, execute_cmd, execute_cmd_out


class VerifySvcMirror(ConfigSvcChain):

    def start_tcpdump(self, session, tap_intf):
        pcap = '/tmp/mirror-%s.pcap' % tap_intf
        cmd = "tcpdump -ni %s udp port 8099 -w %s" % (tap_intf, pcap)
        self.logger.info("Staring tcpdump to capture the mirrored packets.")
        execute_cmd(session, cmd, self.logger)
        return pcap

    def stop_tcpdump(self, session, pcap):
        self.logger.info("Waiting for the tcpdump write to complete.")
        sleep(30)
        cmd = 'kill $(pidof tcpdump)'
        execute_cmd(session, cmd, self.logger)
        cmd = 'tcpdump -r %s | wc -l' % pcap
        out, err = execute_cmd_out(session, cmd, self.logger)
        count = int(out.strip('\n'))
        cmd = 'rm -f %s' % pcap
        execute_cmd(session, cmd, self.logger)
        return count

    def tcpdump_on_analyzer(self, si_prefix):
        sessions = {}
        svm_name = si_prefix + '_1'
        host = self.get_svm_compute(svm_name)
        tapintf = self.get_svm_tapintf(svm_name)
        session = ssh(host['host_ip'], host['username'], host['password'])
        pcap = self.start_tcpdump(session, tapintf)
        sessions.update({svm_name: (session, pcap)})

        return sessions

    def verify_mirror(self, svm_name, session, pcap):
        mirror_pkt_count = self.stop_tcpdump(session, pcap)
        errmsg = "Packets not mirrored to the analyzer VM %s," % (svm_name)
        if mirror_pkt_count == 0:
            self.logger.error(errmsg)
            return [False, errmsg]
        self.logger.info("%s packets are mirrored to the analyzer "
                         "service VM '%s'", mirror_pkt_count, svm_name)

        return [True, None]


def vm_vrouter_flow_count(self):
    cmd = 'flow -l | grep Action | grep -E "F|N" | wc -l '
    result = ''
    output = self.inputs.run_cmd_on_server(self.vm_node_ip, cmd,
                                           self.inputs.host_data[
                                               self.vm_node_ip]['username'],
                                           self.inputs.host_data[self.vm_node_ip]['password'])
    for s in output:
        if s.isdigit():
            result = result + s

    return int(result)
# end vm_vrouter_flow_count
