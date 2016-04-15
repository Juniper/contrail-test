#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import *

from common.neutron.lbaasv2.base import BaseLBaaSTest
import os
import fixtures
import tcutils.wrappers
import time
from vn_test import VNFixture
from vm_test import VMFixture
from test import attr

af_test = 'dual'

HTTP_PORT = 80
HTTPS_PORT = 8080
TCP_PORT = 23

HTTP_PROBE = 'HTTP'
PING_PROBE = 'PING'

class TestLBaaSV2(BaseLBaaSTest):

    @classmethod
    def setUpClass(cls):
        super(TestLBaaSV2, cls).setUpClass()

    @classmethod
    def cleanUp(cls):
        super(TestLBaaSV2, cls).cleanUp()
    # end cleanUp

    @attr(type=['sanity'])
    @preposttest_wrapper
    def test_lbaas_client_pool_in_same_net(self):
        '''Create Lbaas pool, member and vip
           Member, VIP and client all in same VN
           verify: pool, member and vip gets created
           create HMON and verify the association
           verify the HTTP traffic getting loadbalanced using the standby netns
        '''
        result = True
        pool_members = {}
        members=[]

        vn_vm_fix = self.create_vn_and_its_vms(no_of_vm=3)

        vn_vip_fixture = vn_vm_fix[0]
        lb_pool_servers = vn_vm_fix[1][1:]
        client_vm1_fixture = vn_vm_fix[1][0]

        assert client_vm1_fixture.wait_till_vm_is_up()
        for VMs in lb_pool_servers:
            members.append(VMs.vm_ip)

        pool_members.update({'address':members})

        pool_name = get_random_name('mypool')
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = get_random_name('myvip')
        listener_name = get_random_name('HTTP')

        #Call LB fixutre to create LBaaS VIP, Listener, POOL , Member and associate a Health monitor to the pool
        lb = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        #Verify all the creations are success
        assert lb.verify_on_setup(), "Verify LB method failed"

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, lb.vip_ip),\
            "Verify lb method failed"


    # end test_lbaas_client_pool_in_same_net   

    @attr(type=['sanity'])
    @preposttest_wrapper
    def test_lbaas_with_different_fip(self):
        '''Create LB, LISTENER, POOL and MEMBER
            create FIP and associate it to VIP, create a VM in the FIP network
           verify: pool, member and vip gets created
           after vip creation nets ns is created in compute node and haproxy
           process starts , fail otherwise
           Verify different LB Method
        '''
        result = True
        pool_members = {}
        members=[]

        fip_fix = self.useFixture(VNFixture(connections=self.connections, router_external=True))
        client_vm1_fixture = self.create_vm(fip_fix,
                flavor='contrail_flavor_small', image_name='ubuntu')

        vn_vm_fix = self.create_vn_and_its_vms(no_of_vm=3)

        vn_vip_fixture = vn_vm_fix[0]
        lb_pool_servers = vn_vm_fix[1]

        assert client_vm1_fixture.wait_till_vm_is_up()
        for VMs in lb_pool_servers:
            members.append(VMs.vm_ip)

        pool_members.update({'address':members})

        pool_name = get_random_name('mypool')
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = get_random_name('myvip')
        listener_name = get_random_name('RR')

        self.logger.info("Verify Round Robin Method")
        RR_LIST = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        RR_LIST.verify_on_setup()
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, RR_LIST.fip_ip),\
        	"Verify LB Method failed for ROUND ROBIN"

        fip_fix1 = self.useFixture(VNFixture(connections=self.connections, router_external=True))
        client_vm2_fixture = self.create_vm(fip_fix1,
                flavor='contrail_flavor_small', image_name='ubuntu')
        assert client_vm2_fixture.wait_till_vm_is_up()

        ##Disassociate FIP and associate new FIP
        RR_LIST.delete_fip_on_vip()
        RR_LIST.fip_id=None
        RR_LIST.fip_net_id = fip_fix1.uuid
        RR_LIST.create_fip_on_vip()

        assert RR_LIST.verify_on_setup(), "Verify on setup failed after new FIP associated"
        assert self.verify_lb_method(client_vm2_fixture, lb_pool_servers, RR_LIST.fip_ip),\
        	"Verify LB Method failed for ROUND ROBIN"

    @preposttest_wrapper
    def test_lbaas_with_different_lb(self):
        '''Create LB, LISTENER, POOL and MEMBER
            create FIP and associate it to VIP, create a VM in the FIP network
           verify: pool, member and vip gets created
           after vip creation nets ns is created in compute node and haproxy
           process starts , fail otherwise
           Verify different LB Method
        '''
        result = True
        pool_members = {}
        members=[]

        fip_fix = self.useFixture(VNFixture(connections=self.connections, router_external=True))
        client_vm1_fixture = self.create_vm(fip_fix,
                flavor='contrail_flavor_small', image_name='ubuntu')

        vn_vm_fix = self.create_vn_and_its_vms(no_of_vm=3)

        vn_vip_fixture = vn_vm_fix[0]
        lb_pool_servers = vn_vm_fix[1]

        assert client_vm1_fixture.wait_till_vm_is_up()
        for VMs in lb_pool_servers:
            members.append(VMs.vm_ip)

        pool_members.update({'address':members})

        pool_name = get_random_name('mypool')
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = get_random_name('myvip')
        listener_name = get_random_name('RR')

        self.logger.info("Verify Round Robin Method")
        RR_LIST = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        RR_LIST.verify_on_setup()
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, RR_LIST.fip_ip),\
        	"Verify LB Method failed for ROUND ROBIN"

        self.logger.info("Delete Round Robin Listener")
        RR_LIST.delete()

        listener_name = get_random_name('SI')
        lb_method = 'SOURCE_IP'
        pool_name = get_random_name('mypool')

        self.logger.info("Verify Source IP LB Method")
        self.logger.info("Add new Source IP  listener")
        SI_LIST = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        #SI_LIST.add_custom_attr('max_conn', 20)
        SI_LIST.verify_on_setup()

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, SI_LIST.fip_ip,
        	"SOURCE_IP"), "Verify LB Method for SOURCE IP failed"

        self.logger.info("Verify Least Connections LB Method, by modifying the lb_algorithm")
        SI_LIST.network_h.update_lbaas_pool(SI_LIST.pool_uuid, lb_algorithm='LEAST_CONNECTIONS')

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, SI_LIST.fip_ip,
        	"LEAST_CONNECTIONS"), "Verify LB Method failed for LEAST_CONNECTIONS"

    # end test_lbaas_with_different_lb

    @preposttest_wrapper
    def test_lbaas_after_stop_start_vrouter_agent(self):
        '''Create LB, LISTENER, POOL and MEMBER
            create FIP and associate it to VIP, create a VM in the FIP network
           verify: pool, member and vip gets created
           after vip creation nets ns is created in compute node and haproxy
           process starts , fail otherwise
           Verify HTTP traffic passes through standby netns , when the active netns vrouter fails
        '''
        result = True
        pool_members = {}
        members=[]

        fip_fix = self.useFixture(VNFixture(connections=self.connections, router_external=True))
        client_vm1_fixture = self.create_vm(fip_fix,
                flavor='contrail_flavor_small', image_name='ubuntu')

        vn_vm_fix = self.create_vn_and_its_vms(no_of_vm=3)

        vn_vip_fixture = vn_vm_fix[0]
        lb_pool_servers = vn_vm_fix[1]

        assert client_vm1_fixture.wait_till_vm_is_up()
        for VMs in lb_pool_servers:
            members.append(VMs.vm_ip)

        pool_members.update({'address':members})

        pool_name = get_random_name('mypool')
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = get_random_name('myvip')
        listener_name = get_random_name('HTTP')

		#Call LB fixutre to create LBaaS VIP, Listener, POOL , Member and associate a Health monitor to the pool
        lb = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

		#Verify all the creations are success
        lb.verify_on_setup()

		#Now stop the active netns vrouter process
        self.addCleanup(lb.start_active_vrouter)
        lb.stop_active_vrouter()

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, lb.fip_ip),\
        	"Verify lb method failed over standby netns on %s" %lb.standby_vr

    # end test_lbaas_after_stop_start_vrouter_agent

    @preposttest_wrapper
    def test_lbaas_svc_mon_restart(self):
        '''Create LB, LISTENER, POOL and MEMBER
            create FIP and associate it to VIP, create a VM in the FIP network
           verify: pool, member and vip gets created
           after vip creation nets ns is created in compute node and haproxy
           process starts , fail otherwise
           Verify HTTP traffic after restarting the active SVC-monitor
        '''
        result = True
        pool_members = {}
        members=[]

        fip_fix = self.useFixture(VNFixture(connections=self.connections, router_external=True))
        client_vm1_fixture = self.create_vm(fip_fix,
                flavor='contrail_flavor_small', image_name='ubuntu')

        vn_vm_fix = self.create_vn_and_its_vms(no_of_vm=3)

        vn_vip_fixture = vn_vm_fix[0]
        lb_pool_servers = vn_vm_fix[1]

        assert client_vm1_fixture.wait_till_vm_is_up()
        for VMs in lb_pool_servers:
	        members.append(VMs.vm_ip)
        pool_members.update({'address':members})
        pool_name = get_random_name('mypool')
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = get_random_name('myvip')
        listener_name = get_random_name('HTTP')

        HTTP_LIST = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        HTTP_LIST.verify_on_setup()

        TCP_LIST = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol='TCP',
              pool_port=TCP_PORT, members=pool_members, listener_name=get_random_name('TCP'),
              fip_net_id=fip_fix.uuid, vip_port=TCP_PORT, vip_protocol='TCP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=PING_PROBE)

        TCP_LIST.verify_on_setup()

        HTTPS_LIST = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol='HTTPS',
              pool_port=HTTPS_PORT, members=pool_members, listener_name=get_random_name('HTTPS'),
              fip_net_id=fip_fix.uuid, vip_port=HTTPS_PORT, vip_protocol='HTTPS',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=PING_PROBE)

        HTTPS_LIST.verify_on_setup()

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, HTTP_LIST.fip_ip),\
        	"Verify LB failed for ROUND ROBIN"

        self.logger.info("Restart the active Service Monitor")
        HTTP_LIST.restart_active_svc_mon()

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, HTTP_LIST.fip_ip),\
        	"Verify LB failed for ROUND ROBIN after SVC restart"

        #SVC monitor might recreate the netns instance, so verifying after sleep for 60 sec
        time.sleep(60)
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, HTTP_LIST.fip_ip),\
        	"Verify LB failed for ROUND ROBIN after SVC restart"

    # end test_lbaas_svc_mon_restart
