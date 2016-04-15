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
        lb.start_active_vrouter()

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

        http_listener = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        http_listener.verify_on_setup()

        tcp_listener = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol='TCP',
              pool_port=TCP_PORT, members=pool_members, listener_name=get_random_name('TCP'),
              fip_net_id=fip_fix.uuid, vip_port=TCP_PORT, vip_protocol='TCP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=PING_PROBE)

        tcp_listener.verify_on_setup()

        https_listener = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol='HTTPS',
              pool_port=HTTPS_PORT, members=pool_members, listener_name=get_random_name('HTTPS'),
              fip_net_id=fip_fix.uuid, vip_port=HTTPS_PORT, vip_protocol='HTTPS',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=PING_PROBE)

        https_listener.verify_on_setup()

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, http_listener.fip_ip),\
            "Verify LB failed for ROUND ROBIN"

        self.logger.info("Restart the active Service Monitor")
        http_listener.restart_active_svc_mon()

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, http_listener.fip_ip),\
            "Verify LB failed for ROUND ROBIN after SVC restart"

        #SVC monitor might recreate the netns instance, so verifying after sleep for 60 sec
        time.sleep(60)
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, http_listener.fip_ip),\
            "Verify LB failed for ROUND ROBIN after SVC restart"

    # end test_lbaas_svc_mon_restart
