from __future__ import division
from builtins import str
from builtins import range
from past.utils import old_div
from common.dsnat.base import BaseDSNAT
from common.neutron.base import BaseNeutronTest
from security_group import SecurityGroupFixture
from tcutils.wrappers import preposttest_wrapper
import test
import time
from tcutils.util import *
from tcutils.tcpdump_utils import *
from common import isolated_creds
from test import attr

class TestDSNAT(BaseDSNAT):

    @skip_because(min_nodes=2)
    @preposttest_wrapper
    def test_dsnat_udp_basic(self):
        '''
           configure port translation pools in the global vrouter config
           create a test VN , enable SNAT, 
           send UDP traffic from VM to fabric IP and verify the PAT happened, 
               and the port been used in the range
        '''
        port_range = list(range(65000, 65010))
        self.logger.info("configure port translation pool in global vrouter config for both\
            TCP and UDP in the range of %d to %d" %(port_range[0], port_range[-1]))
        pp = []
        pp.append(self.define_port_translation_pool(protocol='udp',
                    start_port=port_range[0],
                    end_port=port_range[-1]))
       
        pp.append(self.define_port_translation_pool(protocol='tcp',
                    start_port=port_range[0],
                    end_port=port_range[-1]))
        #assert self.verify_port_translation_pool(udp_pp)
        assert self.vnc_h.set_port_translation_pool(pp)

        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn1_fixture = self.create_vn_enable_fabric_snat()

        vm1_node_name = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        vm2_node_name = self.inputs.host_data[self.inputs.compute_ips[1]]['name']

        #Launch VM on different compute nodes
        vm1_fixture = self.create_vm(vn1_fixture,
                                     get_random_name('dsnat-vm1'),
                                     image_name='ubuntu-traffic',
                                     node_name=vm1_node_name)
        vm2_fixture = self.create_vm(vn1_fixture,
                                     get_random_name('dsnat-vm2'),
                                     image_name='ubuntu-traffic',
                                     node_name=vm2_node_name)

        #Verify VM is Active
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        assert vm1_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)
        assert vm2_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)

        traffic = {}
        traffic['udp'] = True
        traffic['port'] = 5201
        self.iperf = None

        assert self.verify_flow_with_port(vm1_fixture, vm2_fixture, port_range, **traffic)


    @attr(type=['sanity'])
    @skip_because(min_nodes=2,dpdk_cluster=True)
    @preposttest_wrapper
    def test_dsnat_tcp_basic(self):
        '''
            Configure TCP port translation pool
            send TCP traffic from the VM to the fabric IP
            Verify the Port address translation happened and the 
               port being used in the range of configured
        '''
        port_range = list(range(65000, 65010))
        pp = []
        pp.append(self.define_port_translation_pool(protocol='tcp',
                    start_port=port_range[0],
                    end_port=port_range[-1]))
       
        #assert self.verify_port_translation_pool(tcp_pp)
        assert self.vnc_h.set_port_translation_pool(pp)

        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn1_fixture = self.create_vn_enable_fabric_snat()

        vm1_node_name = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        vm2_node_name = self.inputs.host_data[self.inputs.compute_ips[1]]['name']

        #Launch VM on different compute nodes
        vm1_fixture = self.create_vm(vn1_fixture,
                                     get_random_name('dsnat-vm1'),
                                     image_name='ubuntu-traffic',
                                     node_name=vm1_node_name)
        vm2_fixture = self.create_vm(vn1_fixture,
                                     get_random_name('dsnat-vm2'),
                                     image_name='ubuntu-traffic',
                                     node_name=vm2_node_name)

        #Verify VM is Active
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        assert vm1_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)
        assert vm2_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)

        traffic = {}
        traffic['udp'] = False
        traffic['port'] = 6201
        self.iperf = None

        assert self.verify_flow_with_port(vm1_fixture, vm2_fixture, port_range, **traffic)

    @preposttest_wrapper
    def test_dsnat_with_vhost_policy(self):
        '''
            create a VN and enable fabric SNAT and launch a VM
            set vhost disable policy TRUE
            verify ping between the VN and ping to the external IP
            set vhost disable policy FALSE
            verify that the ping the external IP succeed
        '''

        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn_fixture = self.create_vn_enable_fabric_snat()

        test_vm1 = self.create_vm(vn_fixture, get_random_name('test_vm1'),
                                 image_name='ubuntu')
        assert test_vm1.wait_till_vm_is_up()

        assert test_vm1.verify_fabric_ip_as_floating_ip(vn_fixture.vn_fq_name)

        self.disable_policy_on_vhost0(
            self.inputs.host_data[test_vm1.vm_node_ip]['name'], disable=False)
        self.addCleanup(self.disable_policy_on_vhost0,\
            self.inputs.host_data[test_vm1.vm_node_ip]['name'])
        #with DSNAT enabled on VN, verify the ping to the external IP
        assert test_vm1.ping_with_certainty\
            (self.inputs.host_data[self.inputs.cfgm_ip]['host_data_ip'])

        self.disable_policy_on_vhost0(
            self.inputs.host_data[test_vm1.vm_node_ip]['name'])
        #with DSNAT enabled on VN, verify the ping to the external IP
        assert test_vm1.ping_with_certainty\
            (self.inputs.host_data[self.inputs.cfgm_ip]['host_data_ip'])

    @skip_because(min_nodes=2)
    @preposttest_wrapper
    def test_dsnat_port_modify(self):
        '''
           configure port translation pools in the global vrouter config
           create a test VN , enable SNAT,
           send traffic to exhaust the port translation pool
           modify the port translation pool in the global vrouter config
           and verify the traffic
        '''
        port_range = list(range(65000, 65010))
        self.logger.info("configure port translation pool in global vrouter config for both\
            TCP and UDP in the range of %d to %d" %(port_range[0], port_range[-1]))
        pp = []
        pp.append(self.define_port_translation_pool(protocol='udp',
                    start_port=port_range[0],
                    end_port=port_range[-1]))

        pp.append(self.define_port_translation_pool(protocol='tcp',
                    start_port=port_range[0],
                    end_port=port_range[-1]))
        #assert self.verify_port_translation_pool(udp_pp)
        assert self.vnc_h.set_port_translation_pool(pp)

        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn1_fixture = self.create_vn_enable_fabric_snat()

        vm1_node_name = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        vm2_node_name = self.inputs.host_data[self.inputs.compute_ips[1]]['name']

        #Launch VM on different compute nodes
        vm1_fixture = self.create_vm(vn1_fixture,
                                     get_random_name('dsnat-vm1'),
                                     image_name='ubuntu-traffic',
                                     node_name=vm1_node_name)
        vm2_fixture = self.create_vm(vn1_fixture,
                                     get_random_name('dsnat-vm2'),
                                     image_name='ubuntu-traffic',
                                     node_name=vm2_node_name)

        #Verify VM is Active
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        assert vm1_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)
        assert vm2_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)

        traffic = {}
        traffic['udp'] = True
        traffic['port'] = 5201
        self.iperf = None
        ## Repeat UDP traffic multiple times, to exhaust the pool and verify the flow
        for i in range(len(port_range)):
            self.run_iperf_between_vm_host(vm1_fixture, vm2_fixture.vm_node_ip, vm2_fixture.vm_node_data_ip, **traffic)
        nat_port_used = self.get_nat_port_used_for_flow(vm1_fixture, '17', traffic['port'])
        if len(nat_port_used) > len(port_range) or set(nat_port_used) != set(port_range):
            assert False, ('NAT port allocated, %s, more than the configured'  %nat_port_used)

        port_count = old_div(len(port_range),2)
        self.logger.info('Reduce the port translation pool range or count for UDP to %d' %port_count)
        pp[0] = (self.define_port_translation_pool(protocol='udp',
             port_count=str(port_count)))

        assert self.vnc_h.set_port_translation_pool(pp)
        nat_port_used = self.get_nat_port_used_for_flow(vm1_fixture, '17', traffic['port'])
        if len(nat_port_used) != port_count:
            assert False, ('After reducing port range, expected flows to be\
                reduced to port count, %d, but actual flows are %d' %(port_count, len(nat_port_used)))

        port_count = port_count*5
        self.logger.info('Increase the port translation pool range or count for UDP to %d' %port_count)
        pp[0] = (self.define_port_translation_pool(protocol='udp',
             port_count=str(port_count)))
        assert self.vnc_h.set_port_translation_pool(pp)

        self.logger.info("Increase port range, shouldn't affect the existing flows")
        nat_port_used = self.get_nat_port_used_for_flow(vm1_fixture, '17', traffic['port'])
        if len(nat_port_used) != old_div(port_count,5):
            assert False, ('After increasing port range, expected flows to be\
                same as , %d, but actual flows are %d' %(old_div(port_count,5), len(nat_port_used)))
        ## Repeat UDP traffic multiple times, to exhaust the pool and verify the flow
        for i in range(port_count):
            self.run_iperf_between_vm_host(vm1_fixture, vm2_fixture.vm_node_ip, vm2_fixture.vm_node_data_ip, **traffic)
        nat_port_used = self.get_nat_port_used_for_flow(vm1_fixture, '17', traffic['port'])
        if len(nat_port_used) != port_count:
            assert False, ('After increasing port range, expected flows to be\
                same as , %d, but actual flows are %d' %(port_count, len(nat_port_used)))

    @skip_because(min_nodes=2)
    @preposttest_wrapper
    def test_dsnat_discrete_port_range(self):
        '''
           configure port translation pools in the global vrouter config
           create a test VN , enable SNAT,
           send UDP traffic from VM to fabric IP and verify the PAT happened,
               and the port been used in the range
           configured discrete range of port translation pool of same protocol udp
           send UDP traffic from VM to fabirc IP and verify ports been used in the 
               combined range
        '''
        port_range1 = list(range(65000, 65010))
        self.logger.info("configure port translation pool in global vrouter config for both\
            TCP and UDP in the range of %d to %d" %(port_range1[0], port_range1[-1]))
        pp = []
        pp.append(self.define_port_translation_pool(protocol='udp',
                    start_port=port_range1[0],
                    end_port=port_range1[-1]))

        pp.append(self.define_port_translation_pool(protocol='tcp',
                    start_port=port_range1[0],
                    end_port=port_range1[-1]))
    
        assert self.vnc_h.set_port_translation_pool(pp)
        assert self.verify_port_allocation_in_agent(pp)

        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn1_fixture = self.create_vn_enable_fabric_snat()

        vm1_node_name = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        vm2_node_name = self.inputs.host_data[self.inputs.compute_ips[1]]['name']

        #Launch VM on different compute nodes
        vm1_fixture = self.create_vm(vn1_fixture,
                                     get_random_name('dsnat-vm1'),
                                     image_name='ubuntu-traffic',
                                     node_name=vm1_node_name)
        vm2_fixture = self.create_vm(vn1_fixture,
                                     get_random_name('dsnat-vm2'),
                                     image_name='ubuntu-traffic',
                                     node_name=vm2_node_name)

        #Verify VM is Active
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        assert vm1_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)
        assert vm2_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)

        traffic = {}
        traffic['udp'] = True
        traffic['port'] = 5201
        self.iperf = None

        for i in range(len(port_range1)):
            self.run_iperf_between_vm_host(vm1_fixture, vm2_fixture.vm_node_ip, vm2_fixture.vm_node_data_ip, **traffic)
        nat_port_used = self.get_nat_port_used_for_flow(vm1_fixture, '17', traffic['port'])
        if len(nat_port_used) > len(port_range1) or set(nat_port_used) != set(port_range1):
            assert False, ('NAT port allocated, %s, more than the configured'  %nat_port_used)

        port_range2 = list(range(65100, 65110))
        pp.append(self.define_port_translation_pool(protocol='udp',
                    start_port=port_range2[0],
                    end_port=port_range2[-1]))

        assert self.vnc_h.set_port_translation_pool(pp)
        assert self.verify_port_allocation_in_agent(pp)

        nat_port_used = self.get_nat_port_used_for_flow(vm1_fixture, '17', traffic['port'])
        if len(nat_port_used) > len(port_range1) or set(nat_port_used) != set(port_range1):
            assert False, ('NAT port allocated, %s, more than the configured'  %nat_port_used)
        else:
            self.logger.info("PAT used the configure port translation pool, %s" %nat_port_used)

        for i in range(len(port_range2)):
            self.run_iperf_between_vm_host(vm1_fixture, vm2_fixture.vm_node_ip, vm2_fixture.vm_node_data_ip, **traffic)
        nat_port_used = self.get_nat_port_used_for_flow(vm1_fixture, '17', traffic['port'])
        if len(nat_port_used) > len(port_range1)+len(port_range2) or\
            set(nat_port_used) != set(port_range1).union(set(port_range2)):
            assert False, ('NAT port allocated, %s, more than the configured'  %nat_port_used)
        else:
            self.logger.info("PAT used the configure port translation pool, %s" %nat_port_used)
