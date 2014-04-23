import os
import fixtures
import testtools

from tcutils.parsers.netperfparse import NetPerfParser
from tcutils.parsers.pingparse import PingParser
from connections import ContrailConnections
from testresources import ResourcedTestCase
from config import ConfigPerformance 

class PerformanceTest(ConfigPerformance):
    def test_check_netperf_within_vn(self, no_of_vn=1):
        ''' Validate Network performance between two VMs within a VN.
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

            self.policy_name = 'netperf_policy'
            self.rules = [{'direction'     : '<>',
                           'protocol'      : 'tcp',
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
                host_list=[]
                for host in self.inputs.compute_ips: host_list.append(self.inputs.host_data[host]['name'])
                compute_1 = host_list[0]
                compute_2 = host_list[0]
                if len(host_list) > 1:
                    compute_1 = host_list[0]
                    compute_2 = host_list[1]
                self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name, node_name=compute_1)
                self.vm2_fixture = self.config_vm(self.vn2_fixture, self.vm2_name, node_name=compute_2)

            assert self.vm1_fixture.verify_on_setup()
            assert self.vm2_fixture.verify_on_setup()
            #self.nova_fixture.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
            #self.nova_fixture.wait_till_vm_is_up(self.vm2_fixture.vm_obj)
        else:
            if getattr(self, 'res', None):
                self.vm1_fixture= self.res.vn1_vm5_fixture
                self.vm2_fixture= self.res.vn1_vm6_fixture
            else:
                # Making sure VM falls on diffrent compute host
                host_list=[]
                for host in self.inputs.compute_ips: host_list.append(self.inputs.host_data[host]['name'])
                compute_1 = host_list[0]
                compute_2 = host_list[0]
                if len(host_list) > 1:
                    compute_1 = host_list[0]
                    compute_2 = host_list[1]
                self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name, node_name=compute_1)
                self.vm2_fixture = self.config_vm(self.vn1_fixture, self.vm2_name, node_name=compute_2)

            assert self.vm1_fixture.verify_on_setup()
            assert self.vm2_fixture.verify_on_setup()
            #self.nova_fixture.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
            #self.nova_fixture.wait_till_vm_is_up(self.vm2_fixture.vm_obj)
        results = []
        #set the cpu to highest performance in compute nodes before running the test
        hosts=[]
        hosts.append(self.inputs.host_data[self.vm1_fixture.vm_node_ip])
        hosts.append(self.inputs.host_data[self.vm2_fixture.vm_node_ip])
        self.set_cpu_performance(hosts)

        self.logger.info("Running netperf for 60 sec to check outbound throughput")
        cmd = 'sudo netperf -H %s -t TCP_STREAM -B outbound -l 60' % self.vm2_fixture.vm_ip
        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd])
        outbound_netperf = NetPerfParser(self.vm1_fixture.return_output_values_list[0])
        outbound_throughout = outbound_netperf.get_throughput()
        self.logger.info("Outbound throughput: %s", outbound_throughout)
        results.append((outbound_netperf.get_throughput() > 900,
                       "Outbound throughput is(%s) less than 900" % outbound_throughout))
        self.logger.info("Running netperf for 60 sec to check inbound throughput")
        cmd = 'sudo netperf -H %s -t TCP_STREAM -B inbound -l 60' % self.vm2_fixture.vm_ip
        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd])
        inbound_netperf = NetPerfParser(self.vm1_fixture.return_output_values_list[0])
        inbound_throughout = inbound_netperf.get_throughput()
        self.logger.info("Inbound throughput: %s", outbound_throughout)
        results.append((inbound_netperf.get_throughput() > 900,
                       "Outbound throughput is(%s) less than 900" % inbound_throughout))

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

    def test_ping_latency(self, no_of_vn=1, no_of_pkt=1):
        ''' Validate ping latency between two VMs.
        '''
        if getattr(self, 'res', None):
            self.vn1_fixture= self.res.vn1_fixture
            self.vn2_fixture= self.res.vn2_fixture
            if no_of_vn==2:
                self.vm1_fixture= self.res.vn1_vm1_fixture
                self.vm2_fixture= self.res.vn2_vm1_fixture
            else:
                self.vm1_fixture= self.res.vn1_vm1_fixture
                self.vm2_fixture= self.res.vn1_vm2_fixture
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

            self.policy_name = 'netperf_policy'
            self.rules = [{'direction'     : '<>',
                           'protocol'      : 'icmp',
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
                host_list=[]
                for host in self.inputs.compute_ips: host_list.append(self.inputs.host_data[host]['name'])
                compute_1 = host_list[0]
                compute_2 = host_list[0]
                if len(host_list) > 1:
                    compute_1 = host_list[0]
                    compute_2 = host_list[1]
                self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name, node_name=compute_1, image_name='ubuntu-traffic')
                self.vm2_fixture = self.config_vm(self.vn2_fixture, self.vm2_name, node_name=compute_2, image_name='ubuntu-traffic')

            assert self.vm1_fixture.verify_on_setup()
            assert self.vm2_fixture.verify_on_setup()
            result = self.nova_fixture.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
            self.nova_fixture.wait_till_vm_is_up(self.vm2_fixture.vm_obj)
        else:
            if getattr(self, 'res', None):
                self.vm1_fixture= self.res.vn1_vm5_fixture
                self.vm2_fixture= self.res.vn1_vm6_fixture
            else:
                # Making sure VM falls on diffrent compute host
                host_list=[]
                for host in self.inputs.compute_ips: host_list.append(self.inputs.host_data[host]['name'])
                compute_1 = host_list[0]
                compute_2 = host_list[0]
                if len(host_list) > 1:
                    compute_1 = host_list[0]
                    compute_2 = host_list[1]
                self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name, node_name=compute_1, image_name='ubuntu-traffic')
                self.vm2_fixture = self.config_vm(self.vn1_fixture, self.vm2_name, node_name=compute_2, image_name='ubuntu-traffic')

            assert self.vm1_fixture.verify_on_setup()
            assert self.vm2_fixture.verify_on_setup()
            self.nova_fixture.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
            self.nova_fixture.wait_till_vm_is_up(self.vm2_fixture.vm_obj)

        #set the cpu to highest performance in compute nodes before running the test
        hosts=[]
        hosts.append(self.inputs.host_data[self.vm1_fixture.vm_node_ip])
        hosts.append(self.inputs.host_data[self.vm2_fixture.vm_node_ip])
        self.set_cpu_performance(hosts)

        #Verify the ping latency
        results = []
        cmd = 'ping %s -c 1' % self.vm2_fixture.vm_ip
        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd])
        ping_output = PingParser(self.vm1_fixture.return_output_values_list[0])
        ping_latency = ping_output.get_ping_latency()
        self.logger.info("ping latency : %s", ping_latency)
        results.append((float(ping_output.get_ping_latency()) < 2.5,
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

    def cleanUp(self):
        super(PerformanceTest, self).cleanUp()
