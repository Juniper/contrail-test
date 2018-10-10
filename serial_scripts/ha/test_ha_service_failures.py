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
        return self.reboot_service(
            service_name='kafka',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_schema_multi_failure_using_restart(self):
        ''' Test schema service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='schema',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_svc_monitor_multi_failure_using_restart(self):
        ''' Test svc-monitor service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='svc-monitor',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_device_manager_multi_failure_using_restart(self):
        ''' Test device-manager service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='device-manager',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_config_nodemgr_multi_failure_using_restart(self):
        ''' Test config-nodemgr service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='config-nodemgr',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_control_multi_failure_using_restart(self):
        ''' Test control service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='control',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_dns_multi_failure_using_restart(self):
        ''' Test DNS service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='dns',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_named_multi_failure_using_restart(self):
        ''' Test named service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='named',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_control_nodemgr_multi_failure_using_restart(self):
        ''' Test control-nodemgr service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='control-nodemgr',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_config_cassandra_multi_failure_using_restart(self):
        ''' Test config-cassandra service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='config-cassandra',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_config_zookeeper_multi_failure_using_restart(self):
        ''' Test config-zookeeper service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='config-zookeeper',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_analytics_zookeeper_multi_failure_using_restart(self):
        ''' Test analytics-zookeeper service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='analytics-zookeeper',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_config_rabbitmq_multi_failure_using_restart(self):
        ''' Test config-rabbitmq service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='config-rabbitmq',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_rabbitmq_multi_failure_using_restart(self):
        ''' Test rabbitmq service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='rabbitmq',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_keystone_multi_failure_using_restart(self):
        ''' Test keystone service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='keystone',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_redis_multi_failure_using_restart(self):
        ''' Test redis service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='redis',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_analytics_api_multi_failure_using_restart(self):
        ''' Test analytics-api service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='analytics-api',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_alarm_gen_multi_failure_using_restart(self):
        ''' Test alarm-gen service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='alarm-gen',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_collector_multi_failure_using_restart(self):
        ''' Test collector service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='collector',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_query_engine_multi_failure_using_restart(self):
        ''' Test query-engine service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='query-engine',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_snmp_collector_multi_failure_using_restart(self):
        ''' Test snmp-collector service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='snmp-collector',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_topology_multi_failure_using_restart(self):
        ''' Test topology service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='topology',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_analytics_nodemgr_multi_failure_using_restart(self):
        ''' Test analytics-nodemgr service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='analytics-nodemgr',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_webui_multi_failure_using_restart(self):
        ''' Test webui service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='webui',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_webui_middleware_multi_failure_using_restart(self):
        ''' Test webui-middleware service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='webui-middleware',
            host_ips=self.inputs.inputs.host_ips)

    @preposttest_wrapper
    def test_ha_agent_multi_failure_using_restart(self):
        ''' Test agent service instance failure
            Ensure that that system is operational when multiple 
            instances fail. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM and no packet drop should be observed 
        '''
        return self.reboot_service(
            service_name='agent',
            host_ips=self.inputs.inputs.host_ips)
 
