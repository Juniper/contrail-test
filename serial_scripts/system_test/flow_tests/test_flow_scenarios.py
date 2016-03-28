from string import Template
import time


from common.neutron.base import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because
from tcutils.traffic_utils.hping_traffic import Hping3
from compute_node_test import ComputeNodeFixture
from common.agent.flow_table import FlowTable
from tcutils.traffic_utils.base_traffic import BaseTraffic


class ExtendedFlowTestsBase(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(ExtendedFlowTestsBase, cls).setUpClass()
        cls.vnc_api_h = cls.vnc_lib
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(ExtendedFlowTestsBase, cls).tearDownClass()
    # end tearDownClass

    def check_flow_is_evicted(self, compute_fixture, flow_entry_obj):
        ''' flow_entry_obj : FlowEntry object
    '''
        (f_entry, r_flow_entry) = compute_fixture.get_flow_entry(
            index=flow_entry_obj.index)
        assert f_entry is None, ("TCP flow is not evicted ",
                                 "after it is closed. Flow details: %s" % (f_entry.items))
        assert r_flow_entry is None, ("TCP flow is not evicted ",
                                      "after it is closed. Flow details: %s" % (r_flow_entry.items))
        self.logger.info('TCP flow %s is evicted after TCP close' % (
            flow_entry_obj.index))
        self.logger.info('TCP flow %s is evicted after TCP close' % (
            flow_entry_obj.r_flow_index))
    # check_flow_is_evicted


class SimpleTCPFlowEvictionTests(ExtendedFlowTestsBase):

    ''' Use cirros vms to do simple tcp flow eviction tests
    '''
    @classmethod
    def setUpClass(cls):
        super(SimpleTCPFlowEvictionTests, cls).setUpClass()
        cls.vnc_api_h = cls.vnc_lib
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(SimpleTCPFlowEvictionTests, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_flow_entry_after_tcp_session(self):
        '''
        Check TCP flow eviction on a regular teardown

        Do a netcat based file tcp transfer and check flows get evicted later
        Repeat this 3 times
        '''
        sport = '10001'
        dport = '10000'
        filesize = '10000'
        self.vn1_fixture = self.create_vn()
        self.vn2_fixture = self.create_vn()
        self.vn1_vm1_fixture = self.create_vm(self.vn1_fixture,
                                              image_name='cirros-0.3.0-x86_64-uec')
        self.vn1_vm2_fixture = self.create_vm(self.vn1_fixture,
                                              image_name='cirros-0.3.0-x86_64-uec')
        self.vn1_vm1_fixture.wait_till_vm_is_up()
        self.vn1_vm2_fixture.wait_till_vm_is_up()
        self.vn1_vm1_vrouter_fixture = self.useFixture(ComputeNodeFixture(
            self.connections,
            self.vn1_vm1_fixture.vm_node_ip))
        self.vn1_vm2_vrouter_fixture = self.useFixture(ComputeNodeFixture(
            self.connections,
            self.vn1_vm2_fixture.vm_node_ip))

        for i in range(0, 3):
            self.logger.debug('Iteration : %s' % (i))
            # Do file transfer
            result = self.vn1_vm1_fixture.cirros_nc_file_transfer(
                self.vn1_vm2_fixture,
                size=filesize,
                local_port=sport,
                remote_port=dport)
            assert result, "File transfer between cirros vms itself failed!"

            # Check on source and dest computes that the flow is evicted
            for compute in [self.vn1_vm1_vrouter_fixture,
                            self.vn1_vm2_vrouter_fixture]:
                (flow_entry, rev_flow) = compute.get_flow_entry(
                    source_ip=self.vn1_vm1_fixture.vm_ip,
                    dest_ip=self.vn1_vm2_fixture.vm_ip,
                    proto='tcp',
                    source_port=sport,
                    dest_port=dport,
                    vrf_id=compute.get_vrf_id(self.vn1_fixture.vn_fq_name)
                )
                assert flow_entry is None, ('Flow not evicted ater tcp close.',
                                            ' Flow : %s' % (flow_entry.dump))
                assert rev_flow is None, ('Flow not evicted ater tcp close.',
                                          ' Flow : %s' % (flow_entry.dump))
                self.logger.info('TCP flow is evicted after tcp session close')
            # end for
        # end for
    # end test_flow_entry_after_tcp_session

# end class SimpleTCPFlowEvictionTests


class TCPFlowEvictionTests(ExtendedFlowTestsBase):

    @classmethod
    def setUpClass(cls):
        super(TCPFlowEvictionTests, cls).setUpClass()
        cls.vnc_api_h = cls.vnc_lib
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TCPFlowEvictionTests, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(TCPFlowEvictionTests, self).setUp()
        self.vn1_fixture = self.create_vn()
        self.vn2_fixture = self.create_vn()
        self.vn1_vm1_fixture = self.create_vm(self.vn1_fixture)
        self.vn1_vm2_fixture = self.create_vm(self.vn1_fixture)
        self.vn2_vm1_fixture = self.create_vm(self.vn2_fixture)
        self.vn1_vm1_fixture.wait_till_vm_is_up()
        self.vn1_vm2_fixture.wait_till_vm_is_up()
        self.vn2_vm1_fixture.wait_till_vm_is_up()

        self.vn1_vm1_vrouter_fixture = self.useFixture(ComputeNodeFixture(
            self.connections,
            self.vn1_vm1_fixture.vm_node_ip))
        self.vn1_vm2_vrouter_fixture = self.useFixture(ComputeNodeFixture(
            self.connections,
            self.vn1_vm2_fixture.vm_node_ip))
        self.vn2_vm1_vrouter_fixture = self.useFixture(ComputeNodeFixture(
            self.connections,
            self.vn2_vm1_fixture.vm_node_ip))
    # end setUp

    @preposttest_wrapper
    def test_flow_on_normal_tcp_close(self):
        '''
        Check TCP flow eviction on a regular four-way teardown
        Start a TCP session between vn1_vm1 and vn1_vm2
        Check if the flow is active
        After the TCP session is closed,
        Check that no matching flow exists after it is done
        Validate that the flow is marked inactive

        Repeat this 3 times
        '''
        sport = 10000
        dport = 11000
        self.vn1_vm1_fixture.wait_till_vm_is_up()
        self.vn1_vm2_fixture.wait_till_vm_is_up()

        f_flow_index = None
        r_flow_index = None

        for i in range(0, 3):
            traffic_obj = BaseTraffic.factory(proto='tcp')
            traffic_obj.start(
                self.vn1_vm1_fixture, self.vn1_vm2_fixture, 'tcp',
                sport, dport)
            time.sleep(3)
            flow_table = self.vn1_vm1_vrouter_fixture.get_flow_table(
                evicted=True)
            (flow_entry, junk) = self.vn1_vm1_vrouter_fixture.get_flow_entry(
                flow_table=flow_table,
                source_ip=self.vn1_vm1_fixture.vm_ip,
                dest_ip=self.vn1_vm2_fixture.vm_ip,
                proto='tcp',
                source_port=sport,
                dest_port=dport,
                vrf_id=self.vn1_vm1_vrouter_fixture.get_vrf_id(
                    self.vn1_fixture.vn_fq_name)
            )
            if not f_flow_index:
                f_flow_index = flow_entry.index
                r_flow_index = flow_entry.r_flow_index

            assert not flow_entry.is_flow_evicted(
            ), ("TCP flow shown as evicted",
                " on an existing TCP session: %s" % (flow_entry.items))
            assert f_flow_index == flow_entry.index, ("Flow table not same on",
                                                      " a new TCP session with same 5-tuple. Expected: %s, Got %s" % (
                                                          flow_entry.index, f_flow_index))
            assert r_flow_index == flow_entry.r_flow_index, (
                "Rev flow not same",
                " on new TCP session with same 5-tuple. Expected: %s, Got %s" % (
                    flow_entry.index, f_flow_index))
            (sent, recv) = traffic_obj.stop()
            # Wait for atleast 15 secs for agent to evict the flow
            time.sleep(15)
            self.check_flow_is_evicted(
                self.vn1_vm1_vrouter_fixture, flow_entry)
            assert flow_entry.packets > recv, ("Unexpected Flow pkt count",
                                               "Expected: >%s, Seen: %s" % (recv, flow_entry.packets))
        # end for
    # end test_flow_on_normal_tcp_close

    @preposttest_wrapper
    def test_flow_eviction_on_tcp_rst(self):
        '''
        Check TCP flow eviction TCP session gets closed due to a TCP RST
        '''
        sport = 10000
        self.vn1_vm1_fixture.wait_till_vm_is_up()
        self.vn1_vm2_fixture.wait_till_vm_is_up()
        # Unassigned dest port. TCP session to this port should end with RST
        dport = 26
        traffic_obj = BaseTraffic.factory(proto='tcp')
        traffic_obj.start(self.vn1_vm1_fixture, self.vn1_vm2_fixture, 'tcp',
                          sport, dport)

        traffic_obj.stop()
        time.sleep(15)
        flow_table = self.vn1_vm1_vrouter_fixture.get_flow_table(evicted=True)
        (flow_entry, junk) = self.vn1_vm1_vrouter_fixture.get_flow_entry(
            flow_table=flow_table,
            source_ip=self.vn1_vm1_fixture.vm_ip,
            dest_ip=self.vn1_vm2_fixture.vm_ip,
            proto='tcp',
            source_port=sport,
            dest_port=dport,
            vrf_id=self.vn1_vm1_vrouter_fixture.get_vrf_id(
                self.vn1_fixture.vn_fq_name))

        assert flow_entry is None, ('Flow not evicted ater tcp close. Flow: ',
                                    '%s' % (flow_entry.dump))
        self.logger.info('TCP flow is evicted after a TCP RST')
    # end test_flow_eviction_on_tcp_rst

    @preposttest_wrapper
    def test_hping3_tcp_traffic_for_eviction(self):
        '''
        Between two VMs, have a large number of hping3-based tcp sessions
        which are setup and teared down quickly.
        Validate that hping3 does not report any loss and the corresponding
        flows are evicted
        Repeat this a few times so that the same flow indices are used
        '''
        count = 1000
        # Set flow table size to 2M
        self.vn1_vm1_vrouter_fixture.setup_vrouter_module_params(
            {'vr_flow_entries': str(2 * 1024 * 1024)})
        self.vn1_vm1_fixture.wait_till_vm_is_up()
        self.vn1_vm2_fixture.wait_till_vm_is_up()

        destport = '22'
        baseport = '1000'
        interval = 'u1000'
        # Create flows using hping
        hping_h = Hping3(self.vn1_vm1_fixture,
                         self.vn1_vm2_fixture.vm_ip,
                         syn=True,
                         destport=destport,
                         baseport=baseport,
                         count=count,
                         interval=interval)
        for i in range(0, 5):
            self.logger.info('Iteration : %s' % (i))
            hping_h.start(wait=True)
            (stats, hping_log) = hping_h.stop()
            self.logger.debug('Hping3 log : %s' % (hping_log))
            assert stats['loss'] == '0', ('Some loss seen in hping3 session'
                                          'Stats : %s, Check logs..' % (stats))
            self.logger.info('No packet loss seen with hping traffic')
            # Agent does aggressive tcp flow eviction in 15s
            time.sleep(30)

            # Check if these flows got evicted
            flow_table = self.vn1_vm1_vrouter_fixture.get_flow_table()
            (ff_count, rf_count) = self.vn1_vm1_vrouter_fixture.get_flow_count(
                flow_table=flow_table,
                source_ip=self.vn1_vm1_fixture.vm_ip,
                dest_ip=self.vn1_vm2_fixture.vm_ip,
                proto='tcp',
                dest_port='22',
                vrf_id=self.vn1_vm1_vrouter_fixture.get_vrf_id(
                          self.vn1_fixture.vn_fq_name)
            )
            if ff_count or rf_count:
                self.logger.debug('Flow table : %s' % (flow_table.get_as_table))
            assert ff_count == 0, 'One or more flows not evicted yet. Check logs'
            assert rf_count == 0, 'One or more flows not evicted yet. Check logs'
            self.logger.info('Validated that all hping flows got evicted')
        # end for
    # end test_hping3_tcp_traffic_for_eviction


class ExtendedFlowTests(ExtendedFlowTestsBase):

    @classmethod
    def setUpClass(cls):
        super(ExtendedFlowTests, cls).setUpClass()
        cls.vnc_api_h = cls.vnc_lib
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(ExtendedFlowTests, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    #@skip_because(bug='1530034')
    def test_with_fuzz_bug_1504710(self):
        '''
        This test makes sure that the vrouter doesnt misbehave
        with various IP protocols
        This testcase can fail due to bug 1530034
        But the test is enabled to make sure that vrouter does not crash
        '''

        # TODO
        # Unable to figure out what scapy profile can fuzz
        # packets. Currently use raw scapy code itself
        python_code = Template('''
from scapy.all import *
a=fuzz(IP(dst='$dest_ip')/Raw(RandString(size=300)))
send(a, count=10000, inter=0, iface='eth0')
''')

        vn_fixture = self.create_vn()
        vm1_fixture = self.create_vm(vn_fixture)
        vm2_fixture = self.create_vm(vn_fixture)
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        compute_ips = list(set([vm1_fixture.vm_node_ip,
                                vm2_fixture.vm_node_ip]))
        python_code = python_code.substitute(dest_ip=vm2_fixture.vm_ip)
        vm1_fixture.run_python_code(python_code)
        # Below steps does not really make the ping work consistently
        # Keep the code as is for now
        #self.logger.info('Sometimes pkts from/to VM get stuck,'
        #                 'Restarting agents as a workaround(Bug 1530034)')
        #self.inputs.restart_service('contrail-vrouter-agent', compute_ips)
        #status = Constatuscheck(self.inputs)
        #status.wait_till_contrail_cluster_stable(compute_ips)

        # Now validate that later pings between vms work
        self.do_ping_test(vm1_fixture, vm1_fixture.vm_ip, vm2_fixture.vm_ip)
    # end test_with_fuzz_bug_1504710
