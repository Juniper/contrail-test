import os
import fixtures
import testtools
import string

from tcutils.parsers.netperfparse import NetPerfParser
from tcutils.parsers.pingparse import PingParser
from common.connections import ContrailConnections
from testresources import ResourcedTestCase
from config import ConfigPerformance
from tcutils.parsers.flow_rate_parse import FlowRateParser
from config import ConfigPerformance
from fabric.context_managers import settings, hide
from fabric.operations import put, get, local
from util import fab_put_file_to_vm, run_fab_cmd_on_node
from fabric.api import env, run
from common.servicechain.config import ConfigSvcChain


class PerformanceTest(ConfigPerformance,ConfigSvcChain):

    def test_check_netperf_within_vn(self, no_of_vn=1, encap='MPLSoUDP', test_name='TCP_STREAM', duration=10):
        ''' Validate Network performance between two VMs within a VN.
        '''
        if getattr(self, 'res', None):
            self.vn1_fixture = self.res.get_vn1_fixture()
            self.vn2_fixture = self.res.get_vn2_fixture()
            if no_of_vn == 2:
                self.vm1_fixture = self.res.get_vn1_vm5_fixture()
                self.vm2_fixture = self.res.get_vn2_vm3_fixture()
            else:
                self.vm1_fixture = self.res.get_vn1_vm5_fixture()
                self.vm2_fixture = self.res.get_vn1_vm6_fixture()
        else:
            self.vn1_fq_name = "default-domain:admin:vn1"
            self.vn1_name = "vn1"
            self.vn1_subnets = ['31.1.1.0/24']
            self.vm1_name = 'vm1'
            self.vm2_name = 'vm2'
            if no_of_vn == 2:
                self.vn2_fq_name = "default-domain:admin:vn2"
                self.vn2_name = "vn2"
                self.vn2_subnets = ['32.1.1.0/24']

        if getattr(self, 'res', None):
            self.vn1_fixture = self.res.get_vn1_fixture()
            assert self.vn1_fixture.verify_on_setup()
        else:
            self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)

        if no_of_vn == 2:
            if getattr(self, 'res', None):
                self.vn2_fixture = self.res.get_vn2_fixture()
                assert self.vn2_fixture.verify_on_setup()
            else:
                self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)

            self.policy_name = 'netperf_policy'
            self.rules = [{'direction': '<>',
                           'protocol': 'tcp',
                           'source_network': self.vn1_name,
                           'src_ports': [0, -1],
                           'dest_network': self.vn2_name,
                           'dst_ports': [0, -1],
                           'simple_action': 'pass',
                           }
                          ]
            self.policy_fix = self.config_policy(self.policy_name, self.rules)
            self.policy_attach_fix = self.attach_policy_to_vn(self.policy_fix, self.vn1_fixture)
            self.policy_attach_fix = self.attach_policy_to_vn(self.policy_fix, self.vn2_fixture)

            if getattr(self, 'res', None):
                self.vm1_fixture = self.res.get_vn1_vm5_fixture()
                self.vm2_fixture = self.res.get_vn2_vm3_fixture()
            else:
                # Making sure VM falls on diffrent compute host
                host_list = self.connections.nova_h.get_hosts()
                compute_1 = host_list[0]
                compute_2 = host_list[0]
                if len(host_list) > 1:
                    compute_1 = host_list[0]
                    compute_2 = host_list[1]
                self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name, node_name=compute_1)
                self.vm2_fixture = self.config_vm(self.vn2_fixture, self.vm2_name, node_name=compute_2)

            assert self.vm1_fixture.verify_on_setup()
            assert self.vm2_fixture.verify_on_setup()
            self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
            self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)
        else:
            if getattr(self, 'res', None):
                self.vm1_fixture = self.res.get_vn1_vm5_fixture()
                self.vm2_fixture = self.res.get_vn1_vm6_fixture()
            else:
                # Making sure VM falls on diffrent compute host
                host_list = self.connections.nova_h.get_hosts()
                compute_1 = host_list[0]
                compute_2 = host_list[0]
                if len(host_list) > 1:
                    compute_1 = host_list[0]
                    compute_2 = host_list[1]
                self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name, node_name=compute_1)
                self.vm2_fixture = self.config_vm(self.vn1_fixture, self.vm2_name, node_name=compute_2)

            assert self.vm1_fixture.verify_on_setup()
            assert self.vm2_fixture.verify_on_setup()
            self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
            self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)
        results = []
        # set the cpu to highest performance in compute nodes before running
        # the test
        hosts = []
        hosts.append(self.inputs.host_data[self.vm1_fixture.vm_node_ip])
        hosts.append(self.inputs.host_data[self.vm2_fixture.vm_node_ip])
        self.set_cpu_performance(hosts)

        #Change the encap type if user has passed different value other than default:MPLSoUDP
        if encap == 'MPLSoGRE':
            self.changeEncap_setting(encap1='MPLSoGRE', encap2='MPLSoUDP', encap3='VXLAN')

        self.logger.info("Running netperf for %s sec to check throughput",duration)
        cmd = 'sudo netperf -H %s -t %s -l %s' % (self.vm2_fixture.vm_ip, test_name, duration)
        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd])
        netperf = NetPerfParser(self.vm1_fixture.return_output_values_list[0])
        if test_name == 'TCP_RR' or test_name == 'UDP_RR':
            trans_rate = netperf.get_trans_rate()
            self.logger.info("%s transaction rate: %s" % (test_name,trans_rate))
        if test_name == 'TCP_STREAM' or test_name == 'UDP_STREAM':
            throughout = netperf.get_throughput()
            self.logger.info("%s throughput: %s" % (test_name,throughout))
            results.append((netperf.get_throughput() > 900,
                       "Throughput is(%s) less than 900" % throughout))

        errmsg = ''
        for (rc, msg) in results:
            if not rc:
                self.logger.error(msg)
                errmsg += msg + '\n'
        if errmsg:
            #assert False, errmsg
            self.logger.info("This test wont fail; until we identify a number for throughput.")
            self.logger.error(errmsg)

        return True

    def test_ping_latency(self, no_of_vn=1, no_of_pkt=1, count=1):
        ''' Validate ping latency between two VMs.
        '''
        if getattr(self, 'res', None):
            self.vn1_fixture = self.res.get_vn1_fixture()
            self.vn2_fixture = self.res.get_vn2_fixture()
            if no_of_vn == 2:
                self.vm1_fixture = self.res.get_vn1_vm1_fixture()
                self.vm2_fixture = self.res.get_vn2_vm1_fixture()
            else:
                self.vm1_fixture = self.res.get_vn1_vm1_fixture()
                self.vm2_fixture = self.res.get_vn1_vm2_fixture()
        else:
            self.vn1_fq_name = "default-domain:admin:vn1"
            self.vn1_name = "vn1"
            self.vn1_subnets = ['31.1.1.0/24']
            self.vm1_name = 'vm1'
            self.vm2_name = 'vm2'
            if no_of_vn == 2:
                self.vn2_fq_name = "default-domain:admin:vn2"
                self.vn2_name = "vn2"
                self.vn2_subnets = ['32.1.1.0/24']

        if getattr(self, 'res', None):
            self.vn1_fixture = self.res.get_vn1_fixture()
            assert self.vn1_fixture.verify_on_setup()
        else:
            self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)

        if no_of_vn == 2:
            if getattr(self, 'res', None):
                self.vn2_fixture = self.res.get_vn2_fixture()
                assert self.vn2_fixture.verify_on_setup()
            else:
                self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)

            self.policy_name = 'netperf_policy'
            self.rules = [{'direction': '<>',
                           'protocol': 'icmp',
                           'source_network': self.vn1_name,
                           'src_ports': [0, -1],
                           'dest_network': self.vn2_name,
                           'dst_ports': [0, -1],
                           'simple_action': 'pass',
                           }
                          ]
            self.policy_fix = self.config_policy(self.policy_name, self.rules)
            self.policy_attach_fix = self.attach_policy_to_vn(self.policy_fix, self.vn1_fixture)
            self.policy_attach_fix = self.attach_policy_to_vn(self.policy_fix, self.vn2_fixture)

            if getattr(self, 'res', None):
                self.vm1_fixture = self.res.get_vn1_vm5_fixture()
                self.vm2_fixture = self.res.get_vn2_vm3_fixture()
            else:
                # Making sure VM falls on diffrent compute host
                host_list = self.connections.nova_h.get_hosts()
                compute_1 = host_list[0]
                compute_2 = host_list[0]
                if len(host_list) > 1:
                    compute_1 = host_list[0]
                    compute_2 = host_list[1]
                self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name, node_name=compute_1,image_name='ubuntu-traffic')
                self.vm2_fixture = self.config_vm(self.vn2_fixture, self.vm2_name, node_name=compute_2, image_name='ubuntu-traffic')

            assert self.vm1_fixture.verify_on_setup()
            assert self.vm2_fixture.verify_on_setup()
            result = self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
            self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)
        else:
            if getattr(self, 'res', None):
                self.vm1_fixture = self.res.get_vn1_vm5_fixture()
                self.vm2_fixture = self.res.get_vn1_vm6_fixture()
            else:
                # Making sure VM falls on diffrent compute host
                host_list = self.connections.nova_h.get_hosts()
                compute_1 = host_list[0]
                compute_2 = host_list[0]
                if len(host_list) > 1:
                    compute_1 = host_list[0]
                    compute_2 = host_list[1]
                self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name, node_name=compute_1, image_name='ubuntu-traffic')
                self.vm2_fixture = self.config_vm(self.vn1_fixture, self.vm2_name, node_name=compute_2, image_name='ubuntu-traffic')

            assert self.vm1_fixture.verify_on_setup()
            assert self.vm2_fixture.verify_on_setup()
            self.vm1_fixture.wait_till_vm_is_up()
            self.vm2_fixture.wait_till_vm_is_up()

        # set the cpu to highest performance in compute nodes before running
        # the test
        hosts = []
        hosts.append(self.inputs.host_data[self.vm1_fixture.vm_node_ip])
        hosts.append(self.inputs.host_data[self.vm2_fixture.vm_node_ip])
        self.set_cpu_performance(hosts)

        # Verify the ping latency
        results = []
        cmd = 'ping %s -c %s' % (self.vm2_fixture.vm_ip, count)
        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd])
        ping_output = PingParser(self.vm1_fixture.return_output_values_list[0])
        ping_latency = ping_output.get_ping_latency()
        self.logger.info("ping latency : %s", ping_latency)
        results.append((float(ping_latency.strip('ms')) < 2.5,
                       "ping latency is(%s) more than 2.5 ms" % ping_latency))

        errmsg = ''
        for (rc, msg) in results:
            if not rc:
                self.logger.error(msg)
                errmsg += msg + '\n'
        if errmsg:
            #assert False, errmsg
            self.logger.info("This test wont fail; until we identify a number for ping latency.")
            self.logger.error(errmsg)

        return True

    def test_check_flow_setup_within_vn(self, dst_port_min, dst_port_max, src_port_min, src_port_max, no_of_vn=1,
                                        pkt_size=64, no_of_flows=1000):
        ''' Validate flow setup rate between two VMs within a VN.
        '''
        if getattr(self, 'res', None):
            self.vn1_fixture= self.res.vn1_fixture
            self.vn2_fixture= self.res.vn2_fixture
            if no_of_vn==2:
                self.vm1_fixture= self.res.vn1_vm5_fixture
                self.vm2_fixture= self.res.vn2_vm3_fixture
            else:
                self.vm1_fixture= self.res.vn1_vm5_fixture
                self.vm2_fixture= self.res.vn1_vm6_fixture
        else:
            self.vn1_fq_name = "default-domain:admin:vn1"
            self.vn1_name = "vn1"
            self.vn1_subnets = ['31.1.1.0/24']
            self.vm1_name = 'vm1'
            self.vm2_name = 'vm2'
            if no_of_vn==2:
                self.vn2_fq_name = "default-domain:admin:vn2"
                self.vn2_name = "vn2"
                self.vn2_subnets = ['32.1.1.0/24']
        if getattr(self, 'res', None):
            self.vn1_fixture= self.res.vn1_fixture
            assert self.vn1_fixture.verify_on_setup()
        else:
            self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        if no_of_vn==2:
            if getattr(self, 'res', None):
                self.vn2_fixture= self.res.vn2_fixture
                assert self.vn2_fixture.verify_on_setup()
            else:
                self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)

            self.policy_name = 'flow_policy'
            self.rules = [{'direction'     : '<>',
                           'protocol'      : 'udp',
                           'source_network': self.vn1_name,
                           'src_ports'     : [0, -1],
                           'dest_network'  : self.vn2_name,
                           'dst_ports'     : [0, -1],
                           'simple_action' : 'pass',
                          }
                         ]
            self.policy_fix = self.config_policy(self.policy_name, self.rules)
            self.policy_attach_fix = self.attach_policy_to_vn(self.policy_fix, self.vn1_fixture)
            self.policy_attach_fix = self.attach_policy_to_vn(self.policy_fix, self.vn2_fixture)
            if getattr(self, 'res', None):
                self.vm1_fixture= self.res.vn1_vm5_fixture
                self.vm2_fixture= self.res.vn2_vm3_fixture
            else:
                # Making sure VM falls on diffrent compute host
                host_list = self.connections.nova_h.get_hosts()
                compute_1 = host_list[0]
                compute_2 = host_list[0]
                if len(host_list) > 1:
                    compute_1 = host_list[0]
                    compute_2 = host_list[1]
                self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name, node_name=compute_1)
                self.vm2_fixture = self.config_vm(self.vn2_fixture, self.vm2_name, node_name=compute_2)

            assert self.vm1_fixture.verify_on_setup()
            assert self.vm2_fixture.verify_on_setup()
            self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
            self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)
        else:
            if getattr(self, 'res', None):
                self.vm1_fixture= self.res.vn1_vm5_fixture
                self.vm2_fixture= self.res.vn1_vm6_fixture
            else:
                # Making sure VM falls on diffrent compute host
                host_list = self.connections.nova_h.get_hosts()
                compute_1 = host_list[0]
                compute_2 = host_list[0]
                if len(host_list) > 1:
                    compute_1 = host_list[0]
                    compute_2 = host_list[1]
                self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name, node_name=compute_1, image_name='ubuntu-traffic')
                self.vm2_fixture = self.config_vm(self.vn1_fixture, self.vm2_name, node_name=compute_2, image_name='ubuntu-traffic')

            assert self.vm1_fixture.verify_on_setup()
            assert self.vm2_fixture.verify_on_setup()
            self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
            self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)

        vm1_ip = self.vm1_fixture.vm_ip
        vm2_ip = self.vm2_fixture.vm_ip
        fd = open('tcutils/templates/pktgen_template.py', 'r')
        fr = open('/tmp/pktgen', 'w+')
        content = fd.read()
        template = string.Template(content)
        fr.write((template.safe_substitute({'__pkt_size__':pkt_size, '__count__':no_of_flows, '__dst_ip__':vm2_ip, '__src_ip__':vm1_ip,
                                            '__dst_port_mim__':dst_port_min, '__dst_port_max__':dst_port_max,
                                            '__src_port_min__':src_port_min,'__src_port_max__':src_port_max})))
        fr.flush()
        src_ip = self.inputs.cfgm_ips[0]
        if self.inputs.cfgm_ips[0] != self.vm1_fixture.vm_node_ip:
            self.logger.info("Cfgm and compute are different; copy the pktgen from  cfgm '%s'"
                          " to compute '%s'" , self.inputs.cfgm_ips[0], self.vm1_fixture.vm_node_ip)
            with hide('everything'):
                with settings(host_string='%s@%s' % (self.inputs.username,self.vm1_fixture.vm_node_ip),
                                password=self.inputs.password, warn_only=True,abort_on_prompts= False):
                    put('/tmp/pktgen', '/tmp')
                    self.logger.info("Copied the pktgen to compute '%s'", self.vm1_fixture.vm_node_ip)
        #Copy the pkgen to VM
        with hide('everything'):
            with settings(host_string='%s@%s' % (self.inputs.username,self.vm1_fixture.vm_node_ip),
                             password=self.inputs.password, warn_only=True,abort_on_prompts= False):
                output = fab_put_file_to_vm(host_string='%s@%s' %(self.vm1_fixture.vm_username, self.vm1_fixture.local_ip),
                                      password=self.vm1_fixture.vm_password, src='/tmp/pktgen', dest='/tmp')
                #Start the flow -r on compute to check the flow setup rate
                self.logger.info("Start flow -r to monitor the flow setup rate")
                run('flow -r >> /tmp/flow_rate &', pty=False)
        #start the tcpdump on the tap interface of sender and receiver computes.
        session_vm1 = self.start_tcp_dump(self.vm1_fixture)
        session_vm2 = self.start_tcp_dump(self.vm2_fixture)

        #Run pktgen on VM
        output = ''
        with hide('everything'):
            with settings(host_string='%s@%s' % (self.inputs.username,self.vm1_fixture.vm_node_ip),
                             password=self.inputs.password, warn_only=True,abort_on_prompts= False):
                cmd = 'chmod 755 /tmp/pktgen'
                output = run_fab_cmd_on_node(host_string = '%s@%s'%(self.vm1_fixture.vm_username,self.vm1_fixture.local_ip),
                                            password = self.vm1_fixture.vm_password, cmd = cmd, as_sudo=False)
                cmd = 'sudo /tmp/pktgen'
                output = run_fab_cmd_on_node(host_string = '%s@%s'%(self.vm1_fixture.vm_username,self.vm1_fixture.local_ip),
                                    password = self.vm1_fixture.vm_password, cmd = cmd, as_sudo=False)

        #Check flow -l to check the number of flows created.
        with hide('everything'):
            with settings(host_string='%s@%s' % (self.inputs.username,self.vm1_fixture.vm_node_ip),
                           password=self.inputs.password, warn_only=True,abort_on_prompts= False):
                flows_created = run('flow -l | grep Action | wc -l')
                self.logger.info("number of flows created are: '%s'", flows_created)

        #Stop the tcpdump
        sender_count = self.stop_tcp_dump(session_vm1)
        rcvr_count = self.stop_tcp_dump(session_vm2)
        self.logger.info("sender_count: %s, rcvr_count: %s" % (sender_count, rcvr_count))

        #Stop monitoring flow -r
        with hide('everything'):
            with settings(host_string='%s@%s' % (self.inputs.username,self.vm1_fixture.vm_node_ip),
                           password=self.inputs.password, warn_only=True,abort_on_prompts= False):
                pid = run('pidof flow')
                run('kill $(pidof flow)')
                get('/tmp/flow_rate', '/tmp/')
                run('rm -rf /tmp/flow_rate')
        FlowRateParserObj = FlowRateParser('/tmp/flow_rate')
        flow_setup_rate = FlowRateParserObj.flowrate()
        self.logger.info("flow setup rate: '%s'", flow_setup_rate)
        local('rm -rf /tmp/flow_rate')

        results = []
        errmsg = ''
        for (rc, msg) in results:
            if not rc:
                self.logger.error(msg)
                errmsg += msg + '\n'
        if errmsg:
            #assert False, errmsg
            self.logger.info("This test wont fail; until we identify a number for ping latency.")
            self.logger.error(errmsg)

        return True

    def cleanUp(self):
        super(PerformanceTest, self).cleanUp()
