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
        return self.ha_service_single_failure_test('keystone', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_glance_single_failure(self):
        ''' Test glance service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('glance-api', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_mysql_single_failure(self):
        ''' Test mysql service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('mysql', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_nova_api_single_failure(self):
        ''' Test nova-api service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('nova-api', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_nova_conductor_single_failure(self):
        ''' Test nova conductor service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('nova-conductor', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_nova_scheduler_single_failure(self):
        ''' Test nova scheduler service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('nova-scheduler', [self.inputs.cfgm_ips[0]])

    @test.attr(type=['ha', 'vcenter'])
    @preposttest_wrapper
    @skip_because(ha_setup = 'False')
    def test_ha_api_server_single_failure(self):
        ''' Test api-server service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-api', [self.inputs.cfgm_ips[0]])

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    @skip_because(ha_setup = 'False')
    def test_ha_ifmap_single_failure(self):
        ''' Test ifmap service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('ifmap', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_schema_transformer_single_failure(self):
        ''' Test schema service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret = self.ha_service_single_failure_test('contrail-schema', [self.inputs.cfgm_ips[0]])
        time.sleep(30)
        return ret

    @preposttest_wrapper
    def test_ha_discovery_single_failure(self):
        ''' Test discovery service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-discovery', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_svc_monitor_single_failure(self):
        ''' Test svc monitor service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret = self.ha_service_single_failure_test('contrail-svc-monitor', [self.inputs.cfgm_ips[0]])
        time.sleep(30)
        return ret

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    @skip_because(ha_setup = 'False')
    def test_ha_control_single_failure(self):
        ''' Test contrail-control service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret =  self.ha_service_single_failure_test('contrail-control', [self.inputs.bgp_ips[0]])
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
        return self.ha_service_single_failure_test('contrail-dns', [self.inputs.bgp_ips[0]])

    @preposttest_wrapper
    def test_ha_named_single_failure(self):
        ''' Test named service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-named', [self.inputs.bgp_ips[0]])

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    @skip_because(ha_setup = 'False')
    def test_ha_rabbitmq_single_failure(self):
        ''' Test rabbitmq service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('rabbitmq-server', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_zookeeper_single_failure(self):
        ''' Test zookeeper service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('zookeeper', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_cassandra_single_failure(self):
        ''' Test cassandra service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-database', [self.inputs.ds_server_ip[0]])

    @preposttest_wrapper
    def test_ha_haproxy_single_failure(self):
        ''' Test mysql service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret = self.ha_service_single_failure_test('haproxy', [self.inputs.cfgm_ips[0]])
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
        return self.ha_service_single_failure_test('neutron-server', [self.inputs.cfgm_ips[0]])

#end TestHAServiceSanity





