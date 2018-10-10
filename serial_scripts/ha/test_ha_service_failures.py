from base import HABaseTest 
import time
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because
import test

class TestHAService(HABaseTest):

    @classmethod
    def setUpClass(cls):
        super(TestHAService, cls).setUpClass()

    @test.attr(type=['ha'])
    @preposttest_wrapper
    def test_ha_keystone_single_failure(self):
        ''' Test keystone service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('keystone', [self.inputs.cfgm_ips[0]],
                                                   container='keystone')

    @preposttest_wrapper
    def test_ha_glance_single_failure(self):
        ''' Test glance service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('glance-api', [self.inputs.cfgm_ips[0]],
                                                   container='glance')

    @preposttest_wrapper
    def test_ha_mysql_single_failure(self):
        ''' Test mysql service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('mysql', [self.inputs.cfgm_ips[0]],
                                                   container='mysql')

    @preposttest_wrapper
    def test_ha_nova_api_single_failure(self):
        ''' Test nova-api service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('nova-api', [self.inputs.cfgm_ips[0]],
                                                   container='nova')

    @preposttest_wrapper
    def test_ha_nova_conductor_single_failure(self):
        ''' Test nova conductor service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('nova-conductor', [self.inputs.cfgm_ips[0]],
                                                   container='nova-conductor')

    @preposttest_wrapper
    def test_ha_nova_scheduler_single_failure(self):
        ''' Test nova scheduler service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('nova-scheduler', [self.inputs.cfgm_ips[0]],
                                                   container='nova-scheduler')

    @test.attr(type=['ha'])
    @preposttest_wrapper
    @skip_because(ha_setup = False)
    def test_ha_api_server_single_failure(self):
        ''' Test api-server service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-api', [self.inputs.cfgm_ips[0]],
                                                   container='api-server')

    def test_ha_schema_transformer_single_failure(self):
        ''' Test schema service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret = self.ha_service_single_failure_test('contrail-schema', [self.inputs.cfgm_ips[0]],
                                                  container='schema')
        time.sleep(30)
        return ret

    @preposttest_wrapper
    def test_ha_svc_monitor_single_failure(self):
        ''' Test svc monitor service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret = self.ha_service_single_failure_test('contrail-svc-monitor', [self.inputs.cfgm_ips[0]],
                                                  container='svc-monitor')
        time.sleep(30)
        return ret

    @preposttest_wrapper
    @skip_because(ha_setup = False)
    def test_ha_control_single_failure(self):
        ''' Test contrail-control service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret =  self.ha_service_single_failure_test('contrail-control', [self.inputs.bgp_ips[0]],
                                                   container='control')
        time.sleep(60)
        self.ha_service_restart('contrail-vrouter-agent', self.inputs.compute_ips)
        return ret 

    @preposttest_wrapper
    def test_ha_dns_single_failure(self):
        ''' Test dns service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-dns', [self.inputs.bgp_ips[0]],
                                                   container='dns')

    @preposttest_wrapper
    def test_ha_named_single_failure(self):
        ''' Test named service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-named', [self.inputs.bgp_ips[0]],
                                                   container='named')

    @preposttest_wrapper
    @skip_because(ha_setup = False)
    def test_ha_rabbitmq_single_failure(self):
        ''' Test rabbitmq service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('rabbitmq-server', [self.inputs.cfgm_ips[0]],
                                                   container='rabbitmq')

    @preposttest_wrapper
    def test_ha_zookeeper_single_failure(self):
        ''' Test zookeeper service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('zookeeper', [self.inputs.cfgm_ips[0]],
                                                   container='controller')

    @preposttest_wrapper
    def test_ha_cassandra_single_failure(self):
        ''' Test cassandra service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-database', [self.inputs.ds_server_ip[0]],
                                                   container='config-cassandra')

    @preposttest_wrapper
    def test_ha_haproxy_single_failure(self):
        ''' Test mysql service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret = self.ha_service_single_failure_test('haproxy', [self.inputs.cfgm_ips[0]],
                                                  container='haproxy')
        time.sleep(20)
        return ret
 
#    @preposttest_wrapper
#    def test_ha_keepalived_single_failure(self):
#        ''' Test mysql service instance failure
#            Ensure that that system is operational when a signle service
#            instance fails. System should bypass the failure.
#            Pass crietria: Should be able to spawn a VM 
#        '''
#        return self.ha_service_single_failure_test('keepalived', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_neutron_single_failure(self):
        ''' Test neutron-server service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('neutron-server', [self.inputs.cfgm_ips[0]],
                                                   container='neutron')

#end TestHAServiceSanity

    @test.attr(type=['ha'])
    @preposttest_wrapper
    #@skip_because(ha_setup = False)
    def test_ha_reboot_services(self):
        services_list = ['alarm-gen']
        services_list2 = ['collector', 'query-engine', 'alarm-gen','snmp-collector', 'topology',
                          'analytics-nodemgr', 'webui', 'webui-middleware', 'agent']
        result = {}
        #time.sleep(120)
        for service in services_list:
            result[service] = self.reboot_service(
                service, 
                host_ips=self.inputs.inputs.host_ips)
            time.sleep(10)

    @test.attr(type=['ha'])
    @preposttest_wrapper
    #@skip_because(ha_setup = False)
    def test_ha_stop_services(self):
        services_list = ['alarm-gen']
        result = {}
        for service in services_list:
            result[service] = self.reboot_service(
                service,
                host_ips=self.inputs.inputs.host_ips,
                stop_service=True)
            time.sleep(10)
    
        ### Data traffic verification after rebooting service ###
    
        #return result
        #self.ha_start()
        #self.ha_stop()

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
 
