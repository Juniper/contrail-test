#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import *

from common.neutron.lbaasv2.base import BaseLBaaSTest
from common.neutron.base import BaseNeutronTest
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
    def test_lbaas_with_https(self):
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
        listener_protocol = 'TERMINATED_HTTPS'
        listener_port = 443
        vip_name = get_random_name('myvip')
        listener_name = get_random_name('RR')

        self.logger.info("Verify Round Robin Method")
        rr_listener = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=listener_port, vip_protocol=listener_protocol,
              default_tls_container='tls_container', hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        assert rr_listener.verify_on_setup(), "Verify on setup failed after new FIP associated"
        assert client_vm1_fixture.ping_with_certainty(rr_listener.fip_ip)
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, rr_listener.fip_ip, port=listener_port, https=True),\
            "Verify LB Method failed for ROUND ROBIN"

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
    def test_lbaas_with_sg_vip(self):
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
        rr_listener = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        assert rr_listener.verify_on_setup(), "Verify on setup failed after new FIP associated"
        assert client_vm1_fixture.ping_with_certainty(rr_listener.fip_ip)
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, rr_listener.fip_ip),\
            "Verify LB Method failed for ROUND ROBIN"

        self.logger.info("Apply security group to allow only TCP and verify ping fails")
        default_sg = self.get_default_sg()
        vip_sg=self.create_sg()
        rr_listener.apply_sg_to_vip_vmi([vip_sg.get_uuid()])
        assert client_vm1_fixture.ping_with_certainty(rr_listener.fip_ip, expectation=False)
        #assert not self.verify_lb_method(client_vm1_fixture, lb_pool_servers, rr_listener.fip_ip),\
            #"Expected LB verification to fail, because the flow from the netns to members has to fail "

        self.logger.info("Apply security group to allow only TCP to the member VMs and verify the LB works")
        for server in lb_pool_servers:
            server.add_security_group(vip_sg.get_uuid())
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, rr_listener.fip_ip),\
            "Verify LB Method failed for ROUND ROBIN"

        self.logger.info("Remove the security group and apply the default and verify again")
        rr_listener.apply_sg_to_vip_vmi([default_sg.get_sg_id()])
        for server in lb_pool_servers:
            server.remove_security_group(vip_sg.get_uuid())
            server.add_security_group(default_sg.get_sg_id())
        assert client_vm1_fixture.ping_with_certainty(rr_listener.fip_ip)
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, rr_listener.fip_ip),\
            "Verify LB Method failed for ROUND ROBIN"

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
        rr_listener = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        rr_listener.verify_on_setup()
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, rr_listener.fip_ip),\
            "Verify LB Method failed for ROUND ROBIN"

        fip_fix1 = self.useFixture(VNFixture(connections=self.connections, router_external=True))
        client_vm2_fixture = self.create_vm(fip_fix1,
                flavor='contrail_flavor_small', image_name='ubuntu')
        assert client_vm2_fixture.wait_till_vm_is_up()

        ##Disassociate FIP and associate new FIP
        rr_listener.delete_fip_on_vip()
        rr_listener.fip_id=None
        rr_listener.fip_net_id = fip_fix1.uuid
        rr_listener.create_fip_on_vip()

        assert rr_listener.verify_on_setup(), "Verify on setup failed after new FIP associated"
        assert self.verify_lb_method(client_vm2_fixture, lb_pool_servers, rr_listener.fip_ip),\
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
        rr_listener = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        rr_listener.verify_on_setup()
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, rr_listener.fip_ip),\
            "Verify LB Method failed for ROUND ROBIN"

        self.logger.info("Delete Round Robin Listener")
        rr_listener.delete()

        listener_name = get_random_name('SI')
        lb_method = 'SOURCE_IP'
        pool_name = get_random_name('mypool')

        self.logger.info("Verify Source IP LB Method")
        self.logger.info("Add new Source IP  listener")
        si_listener = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        #si_listener.add_custom_attr('max_conn', 20)
        si_listener.verify_on_setup()

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, si_listener.fip_ip,
            "SOURCE_IP"), "Verify LB Method for SOURCE IP failed"

        self.logger.info("Verify Least Connections LB Method, by modifying the lb_algorithm")
        si_listener.network_h.update_lbaas_pool(si_listener.pool_uuid, lb_algorithm='LEAST_CONNECTIONS')

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, si_listener.fip_ip,
            "LEAST_CONNECTIONS"), "Verify LB Method failed for LEAST_CONNECTIONS"

    # end test_lbaas_with_different_lb

    @preposttest_wrapper
    def test_lbaas_add_remove_members(self):
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

        self.logger.info("Verify after adding few more members")
        for no_of_vm in range(3):
            lb_pool_servers.append(self.create_vm(vn_vip_fixture,
                flavor='contrail_flavor_small', image_name='ubuntu'))
            lb_pool_servers[-1].wait_till_vm_is_up()
            lb_pool_servers[-1].start_webserver(listen_port=80)
            http_listener.create_member(address=lb_pool_servers[-1].vm_ip)

        time.sleep(50)
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, http_listener.fip_ip),\
            "Verify LB failed for ROUND ROBIN"

        self.logger.info("Verify after deleting the one of the member VM")
        http_listener.delete_member(address=lb_pool_servers[-1].vm_ip)

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers[:-1], http_listener.fip_ip),\
            "Verify LB failed for ROUND ROBIN"

        for server in lb_pool_servers[:3]:
            server.start_webserver(listen_port=TCP_PORT)
            time.sleep(15)

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers[:3], http_listener.fip_ip, port=TCP_PORT),\
            "Verify LB failed for ROUND ROBIN"

    # end test_lbaas_add_remove_members

    @preposttest_wrapper
    def test_lbaas_health_monitor(self):
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
        rr_listener = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        rr_listener.verify_on_setup()
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, rr_listener.fip_ip),\
            "Verify LB Method failed for ROUND ROBIN"

        self.logger.info("Verify after stopping webserver from one of the server")
        lb_pool_servers[0].stop_webserver()
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers[1:], rr_listener.fip_ip),\
            "Verify LB Method failed for ROUND ROBIN"

        self.logger.info("Verify after adding few more members, and don't start the webserver on the members")
        for no_of_vm in range(3):
            lb_pool_servers.append(self.create_vm(vn_vip_fixture,
                flavor='contrail_flavor_small', image_name='ubuntu'))
            lb_pool_servers[-1].wait_till_vm_is_up()
            ##lb_pool_servers[-1].start_webserver(listen_port=80)
            rr_listener.create_member(address=lb_pool_servers[-1].vm_ip)

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers[1:-3], rr_listener.fip_ip),\
            "Verify LB Method failed for ROUND ROBIN"

    # end test_lbaas_health_monitor

    @preposttest_wrapper
    def test_update_attr_verify_haproxy_conf(self):
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
        rr_listener = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=HTTP_PORT, members=pool_members, listener_name=listener_name,
              fip_net_id=fip_fix.uuid, vip_port=HTTP_PORT, vip_protocol='HTTP',
              hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type=HTTP_PROBE)

        rr_listener.verify_on_setup()
        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers, rr_listener.fip_ip),\
            "Verify LB Method failed for ROUND ROBIN"

        self.logger.info("Verify haproxy config file after modifiying the delay attribute")
        rr_listener.update_hmon(delay=5)
        assert rr_listener.verify_haproxy_configs_on_setup(),\
            "Verify haproxy config file after modifying the delay attribute failed"

        self.logger.info("Verify haproxy config file after modifiying the max_retries attribute")
        rr_listener.update_hmon(max_retries=6)
        assert rr_listener.verify_haproxy_configs_on_setup(),\
            "Verify haproxy config file after modifying the max_retries failed"

        self.logger.info("Verify haproxy config file after modifiying the timeout attribute")
        rr_listener.update_hmon(timeout=7)
        assert rr_listener.verify_haproxy_configs_on_setup(),\
            "Verify haproxy config file failed, after modifying the timeout attribute"

        rr_listener.update_member(rr_listener.member_ids[0], weight=5)
        assert rr_listener.verify_haproxy_configs_on_setup(),\
            "Verify haproxy config file failed, after modifying the member weight attribute"

    # end test_update_attr_verify_haproxy_conf
