from time import sleep

from common.servicechain.config import ConfigSvcChain
from tcutils.commands import ssh, execute_cmd, execute_cmd_out


class ConfigSvcMirror(ConfigSvcChain):

    def start_tcpdump(self, session, tap_intf):
        pcap = '/tmp/mirror-%s.pcap' % tap_intf
        cmd = 'rm -f %s' % pcap
        execute_cmd(session, cmd, self.logger)
        sleep(5)
        cmd = "tcpdump -ni %s udp port 8099 -w %s" % (tap_intf, pcap)
        self.logger.info("Staring tcpdump to capture the mirrored packets.")
        execute_cmd(session, cmd, self.logger)
        return pcap

    def stop_tcpdump(self, session, pcap):
        self.logger.info("Waiting for the tcpdump write to complete.")
        sleep(30)
        cmd = 'kill $(pidof tcpdump)'
        execute_cmd(session, cmd, self.logger)
        execute_cmd(session, 'sync', self.logger)
        cmd = 'tcpdump -r %s | wc -l' % pcap
        out, err = execute_cmd_out(session, cmd, self.logger)
        count = int(out.strip('\n'))
        cmd = 'rm -f %s' % pcap
        execute_cmd(session, cmd, self.logger)
        return count

    def tcpdump_on_all_analyzer(self, si_fixtures, si_prefix, si_count=1):
        sessions = {}
        for i in range(0, si_count):
            si_fixture = si_fixtures[i]
            svm_name = "__".join(si_fixture.si_fq_name) + "__" + str(1)
            host = self.get_svm_compute(svm_name)
            tapintf = self.get_svm_tapintf(svm_name)
            session = ssh(host['host_ip'], host['username'], host['password'])
            pcap = self.start_tcpdump(session, tapintf)
            sessions.update({svm_name: (session, pcap)})

        return sessions
