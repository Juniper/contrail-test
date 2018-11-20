from base import HABaseTest 
import time
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because
import test

class TestHAService(HABaseTest):

    @classmethod
    def setUpClass(cls):
        super(TestHAService, cls).setUpClass()

    @preposttest_wrapper
    def test_ha_analyticsdb_kafka_multi_failure_using_restart(self):
        ''' Test kafka service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='analytics-kafka')

    @preposttest_wrapper
    def test_ha_schema_multi_failure_using_restart(self):
        ''' Test schema service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='schema')

    @preposttest_wrapper
    def test_ha_svc_monitor_multi_failure_using_restart(self):
        ''' Test svc-monitor service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='svc-monitor')

    @preposttest_wrapper
    def test_ha_device_manager_multi_failure_using_restart(self):
        ''' Test device-manager service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='device-manager')

    @preposttest_wrapper
    def test_ha_config_nodemgr_multi_failure_using_restart(self):
        ''' Test config-nodemgr service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='config-nodemgr')

    @preposttest_wrapper
    def test_ha_control_multi_failure_using_restart(self):
        ''' Test control service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='control')

    @preposttest_wrapper
    def test_ha_dns_multi_failure_using_restart(self):
        ''' Test DNS service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='dns')

    @preposttest_wrapper
    def test_ha_named_multi_failure_using_restart(self):
        ''' Test named service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='named')

    @preposttest_wrapper
    def test_ha_control_nodemgr_multi_failure_using_restart(self):
        ''' Test control-nodemgr service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='control-nodemgr')

    @preposttest_wrapper
    def test_ha_config_cassandra_multi_failure_using_restart(self):
        ''' Test config-cassandra service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='config-cassandra')

    @preposttest_wrapper
    def test_ha_config_zookeeper_multi_failure_using_restart(self):
        ''' Test config-zookeeper service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='config-zookeeper')

    @preposttest_wrapper
    def test_ha_analytics_zookeeper_multi_failure_using_restart(self):
        ''' Test analytics-zookeeper service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='analytics-zookeeper')

    @preposttest_wrapper
    def test_ha_config_rabbitmq_multi_failure_using_restart(self):
        ''' Test config-rabbitmq service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='config-rabbitmq')

    @preposttest_wrapper
    def test_ha_rabbitmq_multi_failure_using_restart(self):
        ''' Test rabbitmq service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='rabbitmq')

    @preposttest_wrapper
    def test_ha_keystone_multi_failure_using_restart(self):
        ''' Test keystone service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='keystone')

    @preposttest_wrapper
    def test_ha_redis_multi_failure_using_restart(self):
        ''' Test redis service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='redis')

    @preposttest_wrapper
    def test_ha_analytics_api_multi_failure_using_restart(self):
        ''' Test analytics-api service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='analytics-api')

    @preposttest_wrapper
    def test_ha_alarm_gen_multi_failure_using_restart(self):
        ''' Test alarm-gen service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='alarm-gen')

    @preposttest_wrapper
    def test_ha_collector_multi_failure_using_restart(self):
        ''' Test collector service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='collector')

    @preposttest_wrapper
    def test_ha_query_engine_multi_failure_using_restart(self):
        ''' Test query-engine service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='query-engine')

    @preposttest_wrapper
    def test_ha_snmp_collector_multi_failure_using_restart(self):
        ''' Test snmp-collector service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='snmp-collector')

    @preposttest_wrapper
    def test_ha_topology_multi_failure_using_restart(self):
        ''' Test topology service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='topology')

    @preposttest_wrapper
    def test_ha_analytics_nodemgr_multi_failure_using_restart(self):
        ''' Test analytics-nodemgr service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='analytics-nodemgr')

    @preposttest_wrapper
    def test_ha_webui_multi_failure_using_restart(self):
        ''' Test webui service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='webui')

    @preposttest_wrapper
    def test_ha_webui_middleware_multi_failure_using_restart(self):
        ''' Test webui-middleware service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='webui-middleware')

    @preposttest_wrapper
    def test_ha_agent_multi_failure_using_restart(self):
        ''' Test agent service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='agent')

    @preposttest_wrapper
    def test_ha_analyticsdb_kafka_multi_failure_using_stop(self):
        ''' Test kafka service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='analytics-kafka',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_schema_multi_failure_using_stop(self):
        ''' Test schema service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='schema',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_svc_monitor_multi_failure_using_stop(self):
        ''' Test svc-monitor service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='svc-monitor',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_device_manager_multi_failure_using_stop(self):
        ''' Test device-manager service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='device-manager',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_config_nodemgr_multi_failure_using_stop(self):
        ''' Test config-nodemgr service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='config-nodemgr',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_control_multi_failure_using_stop(self):
        ''' Test control service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='control',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_dns_multi_failure_using_stop(self):
        ''' Test DNS service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='dns',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_named_multi_failure_using_stop(self):
        ''' Test named service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='named',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_control_nodemgr_multi_failure_using_stop(self):
        ''' Test control-nodemgr service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='control-nodemgr',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_config_cassandra_multi_failure_using_stop(self):
        ''' Test config-cassandra service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='config-cassandra',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_config_zookeeper_multi_failure_using_stop(self):
        ''' Test config-zookeeper service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='config-zookeeper',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_analytics_zookeeper_multi_failure_using_stop(self):
        ''' Test analytics-zookeeper service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='analytics-zookeeper',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_config_rabbitmq_multi_failure_using_stop(self):
        ''' Test config-rabbitmq service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='config-rabbitmq',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_rabbitmq_multi_failure_using_stop(self):
        ''' Test rabbitmq service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='rabbitmq',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_keystone_multi_failure_using_stop(self):
        ''' Test keystone service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='keystone',
            stop_service=True)
    
    @preposttest_wrapper
    def test_ha_redis_multi_failure_using_stop(self):
        ''' Test redis service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='redis',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_analytics_api_multi_failure_using_stop(self):
        ''' Test analytics-api service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='analytics-api',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_alarm_gen_multi_failure_using_stop(self):
        ''' Test alarm-gen service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='alarm-gen',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_collector_multi_failure_using_stop(self):
        ''' Test collector service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='collector',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_query_engine_multi_failure_using_stop(self):
        ''' Test query-engine service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='query-engine',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_snmp_collector_multi_failure_using_stop(self):
        ''' Test snmp-collector service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='snmp-collector',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_topology_multi_failure_using_stop(self):
        ''' Test topology service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='topology',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_analytics_nodemgr_multi_failure_using_stop(self):
        ''' Test analytics-nodemgr service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='analytics-nodemgr',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_webui_multi_failure_using_stop(self):
        ''' Test webui service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='webui',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_webui_middleware_multi_failure_using_stop(self):
        ''' Test webui-middleware service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='webui-middleware',
            stop_service=True)

    @preposttest_wrapper
    def test_ha_agent_multi_failure_using_stop(self):
        ''' Test agent service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.reboot_service(
            service_name='agent',
            stop_service=True)
    
    @preposttest_wrapper
    def test_ha_node_failures(self):
        ''' Test node failure scenarios by rebooting nodes one after the other
            Ensure that that system is operational when single
            node fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.logger.info("Running the test for all but compute nodes")
        self.node_failure_check(
            service_list = [
                'analytics-kafka',
                'schema',
                'svc-monitor',
                'device-manager',
                'config-nodemgr',
                'control',
                'dns',
                'named',
                'control-nodemgr',
                'config-cassandra',
                'config-zookeeper',
                'analytics-zookeeper',
                'config-rabbitmq',
		'rabbitmq',
                'keystone',
		'redis',
		'analytics-api',
		'alarm-gen',
		'collector',
		'query-engine',
		'snmp-collector',
		'topology',
		'analytics-nodemgr',
		'webui',
		'webui-middleware'],
            skip_packet_loss_check=False)

    @preposttest_wrapper
    def test_ha_node_failures_compute(self):
        ''' Test node failure scenarios by rebooting nodes one after the other
            Ensure that that system is operational when single
            node fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        self.logger.info("Running the test for agent nodes")
        self.node_failure_check(
            service_list = ['agent'],
            skip_packet_loss_check=True)
