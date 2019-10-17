from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because
from common.device_connection import NetconfConnection
from common.base import GenericTestBase
from tcutils.collector.analytics_tests import *


class TestDpdkBondStatus(GenericTestBase):

    @preposttest_wrapper
    def test_dpdkbond_status_basic(self):
        ret = True

        if not self.inputs.is_dpdk_cluster:
            raise self.skipTest("Skipping Test. Supported only for dpdk nodes.")
            return False

        dpdk_compute = self.inputs.dpdk_ips[0]

        self.logger.info('Ensure slave members are present in vif --list output.')
        ret = ret & self.agent_inspect[dpdk_compute].validate_bondVifListStatus(bondStatus="UP",slaveStatus="UP")

        self.logger.info('Ensure slave members status is present in agent introspect.')
        ret = ret & self.agent_inspect[dpdk_compute].validate_bondStatus(bondStatus="Active",slaveStatus="UP")

        self.logger.info('Ensure no alarms are present since all bond members are up.')

        multi_instances = False
        if len(self.inputs.collector_ips) > 1:
            multi_instances = True
        verify_alarm_cleared = True

        ret = ret & self.analytics_obj._verify_contrail_alarms(None, 'vrouter', 'vrouter_interface', multi_instances=multi_instances, verify_alarm_cleared=verify_alarm_cleared)

        return ret
    #end test_dpdkbond_status_basic 

    @preposttest_wrapper
    def test_dpdkbond_status_restart(self):
        ret = True

        if not self.inputs.is_dpdk_cluster:
            raise self.skipTest("Skipping Test. Supported only for dpdk nodes.")
            return False

        dpdk_compute = self.inputs.dpdk_ips[0]

        self.inputs.restart_service('contrail-vrouter-agent-dpdk', [dpdk_compute], container='agent-dpdk')

        cip = self.inputs.collector_ips[0]
        self.inputs.restart_service('analytics_collector_1', [cip], container='collector')

        time.sleep(20)

        state, state1 = self.inputs.verify_service_state(cip, service='collector')
        assert state,'contrail collector is inactive'
        state, state1 = self.inputs.verify_service_state(dpdk_compute, service='agent-dpdk')
        assert state,'contrail agent is inactive'
        self.logger.info('contrail agent is active')

        self.logger.info('Ensure slave members are present in vif --list output.')
        ret = ret & self.agent_inspect[dpdk_compute].validate_bondVifListStatus(bondStatus="UP",slaveStatus="UP")

        self.logger.info('Ensure slave members status is present in agent introspect.')
        ret = ret & self.agent_inspect[dpdk_compute].validate_bondStatus(bondStatus="Active",slaveStatus="UP")

        self.logger.info('Ensure no alarms are present since all bond members are up.')

        multi_instances = False
        if len(self.inputs.collector_ips) > 1:
            multi_instances = True
        verify_alarm_cleared = True

        ret = ret & self.analytics_obj._verify_contrail_alarms(None, 'vrouter', 'vrouter_interface', multi_instances=multi_instances, verify_alarm_cleared=verify_alarm_cleared)

        return ret
    #end test_dpdkbond_status_restart 

    @preposttest_wrapper
    def test_dpdkbond_status_flap(self):
        #import pdb;pdb.set_trace()
        ret = True

        if not self.inputs.is_dpdk_cluster:
            raise self.skipTest("Skipping Test. Supported only for dpdk nodes.")
            return False

        mgmt_ip= self.inputs.data_sw_ip
        bond_interface_list = self.inputs.data_sw_compute_bond_interface

        mx_handle = NetconfConnection(host = mgmt_ip,username='root',password='Embe1mpls')
        mx_handle.connect()
        time.sleep(10)

        self.logger.info('Bring down data switch bond interface connected to compute.')

        cmd = []
        for bond_interface in self.inputs.data_sw_compute_bond_interface:
            cmd.append('set interfaces '+bond_interface+' disable')

        cli_output = mx_handle.config(stmts = cmd, timeout = 120)
        time.sleep(20)
        dpdk_compute = self.inputs.dpdk_ips[0]

        self.logger.info('Validate bond/slave interface status.')
        self.logger.info('Ensure slave members are present in vif --list output.')
        ret = ret & self.agent_inspect[dpdk_compute].validate_bondVifListStatus(bondStatus="DOWN",slaveStatus="DOWN")
        self.logger.info('Ensure slave members status is present in agent introspect.')
        ret = ret & self.agent_inspect[dpdk_compute].validate_bondStatus(bondStatus="Inactive",slaveStatus="DOWN")

        self.logger.info('Ensure alarms are present since interface is down.')

        multi_instances = False
        if len(self.inputs.collector_ips) > 1:
            multi_instances = True
        verify_alarm_cleared = False
        ret = ret & self.analytics_obj._verify_contrail_alarms(None, 'vrouter', 'vrouter_interface', multi_instances=multi_instances, verify_alarm_cleared=verify_alarm_cleared)

        self.logger.info('Bring up data switch bond interface connected to compute.')

        cmd = []
        for bond_interface in self.inputs.data_sw_compute_bond_interface:
            cmd.append('delete interfaces '+bond_interface+' disable')
        cli_output = mx_handle.config(stmts = cmd, timeout = 120)
        time.sleep(30)

        self.logger.info('Ensure slave members are present in vif --list output.')
        ret = ret & self.agent_inspect[dpdk_compute].validate_bondVifListStatus(bondStatus="UP",slaveStatus="UP")
        self.logger.info('Ensure slave members status is present in agent introspect.')
        ret = ret & self.agent_inspect[dpdk_compute].validate_bondStatus(bondStatus="Active",slaveStatus="UP")

        self.logger.info('Ensure no alarms are present since all bond members are up.')
        verify_alarm_cleared = True
        ret = ret & self.analytics_obj._verify_contrail_alarms(None, 'vrouter', 'vrouter_interface', multi_instances=multi_instances, verify_alarm_cleared=verify_alarm_cleared)

        return ret
    #end test_dpdkbond_status_flap 

