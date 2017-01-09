import os
import fixtures
import testtools

from vn_test import VNFixture
from vm_test import VMFixture
from common.connections import ContrailConnections
from policy_test import PolicyFixture
from policy.config import AttachPolicyFixture
from time import sleep
from tcutils.commands import ssh, execute_cmd, execute_cmd_out

class ConfigPerformance():

    def config_vm(self, vn_fix, vm_name, node_name=None, image_name='ubuntu-netperf', flavor='contrail_flavor_large'):
        vm_fixture = self.useFixture(VMFixture(
                     project_name=self.inputs.project_name, connections=self.connections,
                     vn_obj=vn_fix.obj, vm_name=vm_name, node_name=node_name, image_name=image_name, flavor=flavor))
        return vm_fixture

    def set_cpu_performance(self, hosts):
        sessions = {}
        cmd = 'for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor ; do echo performance > $f; cat $f; done'
        for i in range(0, 2):
            session = ssh(hosts[i]['host_ip'], hosts[i]['username'], hosts[i]['password'])
            execute_cmd(session, cmd, self.logger)
        return

    def start_tcp_dump(self, vm_fixture):
        sessions =[]
        vm_name = vm_fixture.vm_name
        host = self.inputs.host_data[vm_fixture.vm_node_ip]
        inspect_h = self.agent_inspect[vm_fixture.vm_node_ip]
        tapintf = inspect_h.get_vna_tap_interface_by_ip(vm_fixture.vm_ip)[0]['name']
        pcap = '/tmp/%s.pcap' % tapintf
        cmd = "tcpdump -ni %s udp -w %s" % (tapintf, pcap)
        session = ssh(host['host_ip'], host['username'], host['password'])
        self.logger.info("Staring tcpdump to capture the packets.")
        execute_cmd(session, cmd, self.logger)
        sessions.extend((session, pcap))
        return sessions

    def stop_tcp_dump(self, sessions):
        self.logger.info("Waiting for the tcpdump write to complete.")
        sleep(30)
        cmd = 'kill $(pidof tcpdump)'
        execute_cmd(sessions[0], cmd, self.logger)
        execute_cmd(sessions[0], 'sync', self.logger)
        cmd = 'tcpdump -r %s | wc -l' % sessions[1]
        out, err = execute_cmd_out(sessions[0], cmd, self.logger)
        count = int(out.strip('\n'))
        #cmd = 'rm -f %s' % sessions[1]
        #execute_cmd(sessions[0], cmd, self.logger)
        return count

    def changeEncap_setting(self, encap1='MPLSoUDP', encap2='MPLSoGRE', encap3='VXLAN'):
        self.logger.info('Deleting any Encap before continuing')
        out=self.connections.delete_vrouter_encap()
        if ( out!='No config id found'):
            self.addCleanup(self.connections.set_vrouter_config_encap,out[0],out[1],out[2])

            self.logger.info('Setting new Encap before continuing')
            config_id=self.connections.set_vrouter_config_encap(encap1, encap2, encap3)
            self.logger.info('Created.UUID is %s'%(config_id))
            self.addCleanup(self.connections.delete_vrouter_encap)

            encap_list_to_be_configured = [unicode(encap1),unicode(encap2),unicode(encap3)]
            encap_list_configured=self.connections.read_vrouter_config_encap()
            if encap_list_to_be_configured != encap_list_configured:

                self.logger.error( "Configured Encap Priority order is NOT matching with expected order. Configured: %s,\
                                                  Expected: %s" %(encap_list_configured, encap_list_to_be_configured))
                assert False
            else:
                self.logger.info( "Configured Encap Priority order is matching with expected order. Configured: %s,\
                                                   Expected: %s" %(encap_list_configured,encap_list_to_be_configured))
            return
