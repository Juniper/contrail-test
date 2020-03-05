from common.base import GenericTestBase
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because
from common.device_connection import NetconfConnection
from tcutils.collector.analytics_tests import *


class TestDpdkBondStatus(GenericTestBase):

    @preposttest_wrapper
    @skip_because(dpdk_cluster=False)
    def test_dpdkbond_status_basic(self):

        '''
        Ensure that bond member status is displayed properly for dpdk compute node.
        1. Validate slave and bond member status in 'vif --list' output.
        2. Validate agent introspect shows details of bond & slave members.
        3. Ensure that no alarms are present if bond and slave members are up.
        '''

        dpdk_compute = self.inputs.dpdk_ips[0]

        self.logger.info('Ensure slave members are present in vif --list output.')
        assert self.agent_inspect[dpdk_compute].validate_bondVifListStatus(bondStatus="UP",slaveStatus="UP") ,'vif --list output not as expected.'

        self.logger.info('Ensure slave members status is present in agent introspect.')
        assert self.agent_inspect[dpdk_compute].validate_bondStatus(bondStatus="Active",slaveStatus="UP") ,'agent introspect status  not as expected.'

        self.logger.info('Ensure no alarms are present since all bond members are up.')

        multi_instances = False
        if len(self.inputs.collector_ips) > 1:
            multi_instances = True
        verify_alarm_cleared = True

        assert self.analytics_obj._verify_contrail_alarms(None, 'vrouter', 'vrouter_interface', multi_instances=multi_instances, verify_alarm_cleared=verify_alarm_cleared) , 'Alarms not not cleared'

        return True
    #end test_dpdkbond_status_basic 

    @preposttest_wrapper
    @skip_because(dpdk_cluster=False)
    def test_dpdkbond_status_restart(self):

        '''
        Ensure that bond member status is displayed properly for dpdk compute node after agent restart.
        1. Validate slave and bond member status in 'vif --list' output after agent restart.
        2. Validate agent introspect shows details of bond & slave members after agent restart.
        3. Ensure that no alarms are present if bond and slave members are up.
        '''

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
        assert self.agent_inspect[dpdk_compute].validate_bondVifListStatus(bondStatus="UP",slaveStatus="UP") ,'vif --list output not as expected.'

        self.logger.info('Ensure slave members status is present in agent introspect.')
        assert self.agent_inspect[dpdk_compute].validate_bondStatus(bondStatus="Active",slaveStatus="UP") ,'agent introspect status  not as expected.'

        self.logger.info('Ensure no alarms are present since all bond members are up.')

        multi_instances = False
        if len(self.inputs.collector_ips) > 1:
            multi_instances = True
        verify_alarm_cleared = True

        assert self.analytics_obj._verify_contrail_alarms(None, 'vrouter', 'vrouter_interface', multi_instances=multi_instances, verify_alarm_cleared=verify_alarm_cleared) , 'Alarms not not cleared'

        return True
    #end test_dpdkbond_status_restart 

    @preposttest_wrapper
    @skip_because(dpdk_cluster=False)
    def test_dpdkbond_status_flap(self):

        '''
        Ensure that bond member status is displayed properly for dpdk compute node after bringing down bond interface.
        1. Bring down bond member by disabling ae link in data switch.
        2. Validate agent introspect / vif ouptus shows proper status.
        3. Ensure that alarms are raised on bringing down interface.
        '''

        mgmt_ip= self.inputs.data_sw_ip
        bond_interface_list = self.inputs.data_sw_compute_bond_interface
        if (mgmt_ip is None) or (bond_interface_list is None):
            raise self.skipTest("Skipping Test. Need management switch IP and bond interface details.")
        handle = NetconfConnection(host = mgmt_ip,username='root',password='Embe1mpls')
        handle.connect()
        time.sleep(10)

        self.logger.info('Bring down data switch bond interface connected to compute.')
    
        self.addCleanup(self.cleanup_data_sw, mgmt_ip)

        cmd = []
        for bond_interface in self.inputs.data_sw_compute_bond_interface:
            cmd.append('set interfaces '+bond_interface+' disable')

        cli_output = handle.config(stmts = cmd, timeout = 120)
        time.sleep(20)
        dpdk_compute = self.inputs.dpdk_ips[0]

        self.logger.info('Validate bond/slave interface status.')
        self.logger.info('Ensure slave members are present in vif --list output.')
        assert self.agent_inspect[dpdk_compute].validate_bondVifListStatus(bondStatus="DOWN",slaveStatus="DOWN")
        self.logger.info('Ensure slave members status is present in agent introspect.')
        assert self.agent_inspect[dpdk_compute].validate_bondStatus(bondStatus="Inactive",slaveStatus="DOWN")

        self.logger.info('Ensure alarms are present since interface is down.')

        multi_instances = False
        if len(self.inputs.collector_ips) > 1:
            multi_instances = True
        verify_alarm_cleared = False
        assert self.analytics_obj._verify_contrail_alarms(None, 'vrouter', 'vrouter_interface', multi_instances=multi_instances, verify_alarm_cleared=verify_alarm_cleared)

        self.logger.info('Bring up data switch bond interface connected to compute.')

        cmd = []
        for bond_interface in self.inputs.data_sw_compute_bond_interface:
            cmd.append('delete interfaces '+bond_interface+' disable')
        cli_output = handle.config(stmts = cmd, timeout = 120)
        time.sleep(30)

        self.logger.info('Ensure slave members are present in vif --list output.')
        assert self.agent_inspect[dpdk_compute].validate_bondVifListStatus(bondStatus="UP",slaveStatus="UP")
        self.logger.info('Ensure slave members status is present in agent introspect.')
        assert self.agent_inspect[dpdk_compute].validate_bondStatus(bondStatus="Active",slaveStatus="UP")

        self.logger.info('Ensure no alarms are present since all bond members are up.')
        verify_alarm_cleared = True
        assert self.analytics_obj._verify_contrail_alarms(None, 'vrouter', 'vrouter_interface', multi_instances=multi_instances, verify_alarm_cleared=verify_alarm_cleared)

        return True
    #end test_dpdkbond_status_flap 

    def cleanup_data_sw(self, ip):
        '''
            Cleanup configs done on data s/w.
        '''

        handle = NetconfConnection(host = ip,username='root',password='Embe1mpls')
        handle.connect()

        cmd = []
        for bond_interface in self.inputs.data_sw_compute_bond_interface:
            cmd.append('set interfaces '+bond_interface+' disable')
        for bond_interface in self.inputs.data_sw_compute_bond_interface:
            cmd.append('delete interfaces '+bond_interface+' disable')
        cli_output = handle.config(stmts = cmd, timeout = 120)
        assert (not('failed' in cli_output)), "Not able to push config."
        handle.disconnect()

    # end cleanup_data_sw


