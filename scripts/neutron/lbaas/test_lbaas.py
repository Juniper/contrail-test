import os
import fixtures
import testtools
import datetime

from vn_test import *
from vm_test import *
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import run_fab_cmd_on_node

from common.openstack_libs import neutron_client_exception as NeutronClientException

from common.neutron.lbaas.base import BaseTestLbaas
import test


class TestLbaas(BaseTestLbaas):

    @classmethod
    def setUpClass(cls):
        super(TestLbaas, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestLbaas, cls).tearDownClass()

    @preposttest_wrapper
    def test_create_pool_member_vip(self):
        '''Create Lbaas pool, member and vip
           verify: pool, member and vip gets created
           after vip creation nets ns is created in compute node and haproxy
           process starts , fail otherwise
        '''
        result = True
        vn_pool = get_random_name('vn_pool')
        vn_vip = get_random_name('vn_vip')
        vn_pool_subnets = ['10.1.1.0/24']
        vn_vip_subnets = ['20.1.1.0/24']
        pool_vm1 = get_random_name('server1')

        vn_pool_fixture = self.create_vn(vn_pool, vn_pool_subnets)
        assert vn_pool_fixture.verify_on_setup(), "vn %s verification failed" % vn_pool
        vn_vip_fixture = self.create_vn(vn_vip, vn_vip_subnets)
        assert vn_vip_fixture.verify_on_setup(), "vn %s verification failed" % vn_vip
        pool_vm1_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')
        assert pool_vm1_fixture.wait_till_vm_is_up(), "vm %s not up" % pool_vm1

        pool_name = 'mypool'
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = 'myvip'

        #create lb pool
        self.logger.info("creating lb pool:%s" % (pool_name))
        lb_pool = self.create_lb_pool(pool_name, lb_method, protocol, vn_pool_fixture.vn_subnet_objs[0]['id'])
        assert lb_pool, "lb pool create failed"
        #api server verification
        assert self.verify_lb_pool_in_api_server(lb_pool['id']), \
               "API server verification failed for pool with pool id %s" % (lb_pool['id'])
        pool_uuid = lb_pool['id']

        #create lb member
        self.logger.info("creating lb member")
        lb_member = self.create_lb_member(pool_vm1_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member, "lb member create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member['id']), \
              "API server verification failed for member with id %s" % (lb_member['id'])

        #create vip
        self.logger.info("creating lb vip:%s" % (vip_name))
        lb_vip = self.create_vip(vip_name, protocol, protocol_port, vn_vip_fixture.vn_subnet_objs[0]['id'], lb_pool['id'])
        assert lb_vip, "lb vip create failed"
        #api server verification
        assert self.verify_vip_in_api_server(lb_vip['id']), \
               "API server verification failed for vip with vip id %s" % (lb_vip['id'])
        #TODO : agent verification

        pool_names = []
        vip_names = []
        pool_list = self.quantum_h.list_lb_pools()
        assert pool_list, "failed to get the pool list"
        for pool in pool_list:
            pool_names.append(pool['name'])
        assert pool_name in pool_names, "pool %s is not present in the pool list" % (pool_name)

        vip_list = self.quantum_h.list_vips()
        for vip in vip_list:
            vip_names.append(vip['name'])
        assert vip_name in vip_names, "vip %s is not present in the vip list" % (vip_name)

        #sleep for 10 sec netns to get created
        sleep(10)

        #Check if nets ns got created and haproxy running in compute nodes after vip creation
        result,errmsg = self.verify_active_standby(self.inputs.compute_ips, pool_uuid)
        assert result, errmsg

    # end test_create_pool_member_vip

    @preposttest_wrapper
    def test_delete_pool_in_use(self):
        '''Create Lbaas pool,3 member,Health monitor and vip
           associate them with pool
           Try to delete the POOL in use and verify proper error msg is thrown and
           it doesnt initiate the delete of associated vip, HM and members
        '''
        result = True
        vn_pool = get_random_name('vn_pool')
        vn_vip = get_random_name('vn_vip')
        vn_pool_subnets = ['10.1.1.0/24']
        vn_vip_subnets = ['20.1.1.0/24']
        pool_vm1 = get_random_name('server1')
        pool_vm2 = get_random_name('server2')
        pool_vm3 = get_random_name('server3')

        vn_pool_fixture = self.create_vn(vn_pool, vn_pool_subnets)
        assert vn_pool_fixture.verify_on_setup(), "vn %s verification failed" % vn_pool
        vn_vip_fixture = self.create_vn(vn_vip, vn_vip_subnets)
        assert vn_vip_fixture.verify_on_setup(), "vn %s verification failed" % vn_vip
        pool_vm1_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm2_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm2,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm3_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm3,
                flavor='contrail_flavor_small', image_name='ubuntu')

        assert pool_vm1_fixture.wait_till_vm_is_up()
        assert pool_vm2_fixture.wait_till_vm_is_up()
        assert pool_vm3_fixture.wait_till_vm_is_up()

        pool_name = 'mypool'
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = 'myvip'
        hm_delay = 10
        hm_max_retries = 3
        hm_probe_type = 'HTTP'
        hm_timeout = 5

        #create lb pool
        self.logger.info("creating lb pool:%s" % (pool_name))
        lb_pool = self.create_lb_pool(pool_name, lb_method, protocol, vn_pool_fixture.vn_subnet_objs[0]['id'])
        assert lb_pool, "lb pool create failed"
        #api server verification
        assert self.verify_lb_pool_in_api_server(lb_pool['id']), \
               "API server verification failed for pool with pool id %s" % (lb_pool['id'])
        pool_uuid = lb_pool['id']

        #create lb member
        self.logger.info("creating lb member")
        lb_member1 = self.create_lb_member(pool_vm1_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member1, "lb member create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member1['id']), \
              "API server verification failed for member with id %s" % (lb_member1['id'])
        lb_member2 = self.create_lb_member(pool_vm2_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member2, "lb member create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member2['id']), \
              "API server verification failed for member with id %s" % (lb_member2['id'])
        lb_member3 = self.create_lb_member(pool_vm3_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member3, "lb member create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member3['id']), \
              "API server verification failed for member with id %s" % (lb_member3['id'])

        #Create VIP
        self.logger.info("creating lb vip:%s" % (vip_name))
        lb_vip = self.create_vip(vip_name, protocol, protocol_port, vn_vip_fixture.vn_subnet_objs[0]['id'], lb_pool['id'])
        assert lb_vip, "lb vip create failed"
        #api server verification
        assert self.verify_vip_in_api_server(lb_vip['id']), \
               "API server verification failed for vip with vip id %s" % (lb_vip['id'])
        #TODO : agent verification

        #sleep for 10 sec netns to get created
        sleep(10)

        #verify with vip creation netns is created and haproxy is running
        result,errmsg = self.verify_active_standby(self.inputs.compute_ips, pool_uuid)
        assert result, errmsg

        #Create HM and assocuate with pool
        self.logger.info("creating healthmonitor")
        healthmonitor = self.create_health_monitor(hm_delay, hm_max_retries, hm_probe_type, hm_timeout)
        assert self.verify_healthmonitor_in_api_server(healthmonitor['id']), \
               "API server verification failed for healthmonitor with id %s" % (healthmonitor['id'])

        #Associate HM to pool
        self.logger.info("associating healthmonitor to pool %s" % (lb_pool['name']))
        self.associate_health_monitor(lb_pool['id'], healthmonitor['id'])

        #Check if Health monitor is associated with the pool
        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        if pool['health_monitors'][0] == healthmonitor['id']:
            self.logger.info("pool %s is associated with healthmonitor %s" % (lb_pool['name'], pool['health_monitors']))
        else:
           assert False, "pool %s is not associated with healthmonitor %s" %(lb_pool['name'], healthmonitor['id'])

        #verify in API server whether HM is associated with pool
        self.logger.info("Verify in API server whether pool is associaed with Healthmonitor")
        result,msg = self.verify_healthmonitor_association_in_api_server(lb_pool['id'], healthmonitor['id'])
        assert result, msg

        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        associated_vip = pool['vip_id']
        associated_members = pool['members']
        associated_hm = pool['health_monitors']

        #Try to delete the pool with VIP,members and HM associated
        self.logger.info("Try to delete the pool is use")
        try:
            self.quantum_h.delete_lb_pool(lb_pool['id'])
        except NeutronClientException, e:
            self.logger.debug("Execption: (%s) raised while deleting the pool, as we"
                             " tried to delete the pool in use" % (e))
            errmsg = 'Request Failed: internal server error while processing your request'
            if errmsg in e.message:
                self.logger.debug("Delete pool in use ended with 'internal server error'"
                                  "proper error message should have been given, failing the test")
                assert False, ("Internal server error while deleting the pool in use."
                               " Expected proper error msg here.")

        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        if not pool:
            assert False, ("Expected pool with id %s to be present.But could not get the pool details"
                           "  after we tried to delete this pool in use" % (lb_pool['id']))

        #Checking to see if VIP is not deleted with pool delete
        vip = self.quantum_h.show_vip(associated_vip)
        if vip:
            self.logger.info("Vip with id %s present. Pool delete did not initiate the vip delete."
                              % (associated_vip))
        else:
            assert False, ("Expected vip with id %s to be present.But could not get the vip details"
                           "  after we tried to delete associated pool %s"
                           % (associated_vip, lb_pool['id']))

        #Checking to see if pool delete did not delete the members
        for member_id in associated_members:
            member = self.quantum_h.show_lb_member(member_id)
            if member:
                self.logger.info("Member with id %s present. Pool delete did not initiate the delete of"
                                  " associated member" % member_id)
            else:
                assert False, ("Expected member with id %s to be present. But could not get the member"
                                " details, after we tried to deleted the associated pool %s"
                                % (member_id, lb_pool['id']))

        #Verify if the pool delete did not delete the HM
        health_monitor = self.quantum_h.get_health_monitor(associated_hm[0])
        if health_monitor:
            self.logger.info("Health monitor with id %s present. Pool delete did not initiate"
                             " the health monitor delete." % (associated_hm))
        else:
            assert False, ("Expected health monitor with id %s to be present.But could not get"
                           " the health monitor details after we tried to delete associated pool"
                           " %s" % (associated_hm, lb_pool['id']))
    # end test_delete_pool_in_use

    @preposttest_wrapper
    def test_member_delete(self):
        '''Create Lbaas pool,3 member associate them with pool
           Delete one of the member and verify member gets deleted and the
           pool gets updated
        '''
        result = True
        vn_pool = get_random_name('vn_pool')
        vn_vip = get_random_name('vn_vip')
        vn_pool_subnets = ['10.1.1.0/24']
        vn_vip_subnets = ['20.1.1.0/24']
        pool_vm1 = get_random_name('server1')
        pool_vm2 = get_random_name('server2')
        pool_vm3 = get_random_name('server3')

        vn_pool_fixture = self.create_vn(vn_pool, vn_pool_subnets)
        assert vn_pool_fixture.verify_on_setup(), "vn %s verification failed" % vn_pool
        vn_vip_fixture = self.create_vn(vn_vip, vn_vip_subnets)
        assert vn_vip_fixture.verify_on_setup(), "vn %s verification failed" % vn_vip
        pool_vm1_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm2_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm2,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm3_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm3,
                flavor='contrail_flavor_small', image_name='ubuntu')

        assert pool_vm1_fixture.wait_till_vm_is_up()
        assert pool_vm2_fixture.wait_till_vm_is_up()
        assert pool_vm3_fixture.wait_till_vm_is_up()

        pool_name = 'mypool'
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80

        #create lb pool
        self.logger.info("creating lb pool:%s" % (pool_name))
        lb_pool = self.create_lb_pool(pool_name, lb_method, protocol, vn_pool_fixture.vn_subnet_objs[0]['id'])
        assert lb_pool, "lb pool create failed"
        #api server verification
        assert self.verify_lb_pool_in_api_server(lb_pool['id']), \
               "API server verification failed for pool with pool id %s" % (lb_pool['id'])
        pool_uuid = lb_pool['id']

        #create lb member
        self.logger.info("creating lb member")
        lb_member1 = self.create_lb_member(pool_vm1_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member1, "lb member create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member1['id']), \
              "API server verification failed for member with id %s" % (lb_member1['id'])
        lb_member2 = self.create_lb_member(pool_vm2_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member2, "lb member create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member2['id']), \
              "API server verification failed for member with id %s" % (lb_member2['id'])
        lb_member3 = self.create_lb_member(pool_vm3_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member3, "lb member create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member3['id']), \
              "API server verification failed for member with id %s" % (lb_member3['id'])

        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        associated_members = pool['members']

        if lb_member2['id'] in associated_members:
            self.logger.info("member with id %s present in member list associated with pool"
                              % (lb_member2['id']))
        else:
            errmsg = ("member with id %s not present in member list associated with pool,"
                      " not continuing the test failing the test here" % (lb_member2['id']))
            assert False, errmsg
        member_list = self.quantum_h.list_lb_members()
        out = False
        errmsg = ("member with id %s not present in member list, not continuing the test"
                  " failing the test here" % (lb_member2['id']))
        for member in member_list:
            if member['id'] == lb_member2['id']:
                self.logger.info("member with id %s present in member list" % (lb_member2['id']))
                out = True
                break
        assert out, errmsg

        #Delete one of the lb member
        self.logger.info("deleting the lb member %s" % lb_member2['id'])
        self.quantum_h.delete_lb_member(lb_member2['id'])
        self.remove_method_from_cleanups((self.quantum_h.delete_lb_member, (lb_member2['id'],), {}))

        #Verify in the API server if the member is deleted
        self.verify_on_member_delete(lb_member2['id'])

        #Verify the member list
        member_list = self.quantum_h.list_lb_members()
        errmsg = ("member with id %s still present in member list even after member delete"
                  " member list didnt get updated" % (lb_member2['id']))
        for member in member_list:
            if member['id'] == lb_member2['id']:
                assert False, errmsg
        self.logger.info("member with id %s not present in member list after member delete"
                         % (lb_member2['id']))

        #Verfy if the pool is updated
        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        members_associated = pool['members']
        if lb_member2['id'] not in members_associated:
            self.logger.info("member with id %s not present in member list associated with"
                             " pool after member is deleted"  % (lb_member2['id']))
        else:
            errmsg = ("member with id %s still  present in member list associated with pool,"
                      " even after member delete. Pool member list is not geting updated"
                       % (lb_member2['id']))
            assert False, errmsg

    # end test_member_delete

    @preposttest_wrapper
    def test_vip_delete(self):
        '''Create Lbaas pool and vip associate vip with pool
           Delete vip and verify vip gets deleted and the
           pool gets updated
        '''
        result = True
        vn_pool = get_random_name('vn_pool')
        vn_vip = get_random_name('vn_vip')
        vn_pool_subnets = ['10.1.1.0/24']
        vn_vip_subnets = ['20.1.1.0/24']

        vn_pool_fixture = self.create_vn(vn_pool, vn_pool_subnets)
        assert vn_pool_fixture.verify_on_setup(), "vn %s verification failed" % vn_pool
        vn_vip_fixture = self.create_vn(vn_vip, vn_vip_subnets)
        assert vn_vip_fixture.verify_on_setup(), "vn %s verification failed" % vn_vip

        pool_name = 'mypool'
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = 'myvip'

        #create lb pool
        self.logger.info("creating lb pool:%s" % (pool_name))
        lb_pool = self.create_lb_pool(pool_name, lb_method, protocol, vn_pool_fixture.vn_subnet_objs[0]['id'])
        assert lb_pool, "lb pool create failed"
        #api server verification
        assert self.verify_lb_pool_in_api_server(lb_pool['id']), \
               "API server verification failed for pool with pool id %s" % (lb_pool['id'])
        pool_uuid = lb_pool['id']

        #Create VIP
        self.logger.info("creating lb vip:%s" % (vip_name))
        lb_vip = self.create_vip(vip_name, protocol, protocol_port, vn_vip_fixture.vn_subnet_objs[0]['id'], lb_pool['id'])
        assert lb_vip, "lb vip create failed"
        #api server verification
        assert self.verify_vip_in_api_server(lb_vip['id']), \
               "API server verification failed for vip with vip id %s" % (lb_vip['id'])
        #TODO : agent verification

        #sleep for 10 sec netns to get created
        sleep(10)

        #verify with vip creation netns is created and haproxy is running
        result,errmsg = self.verify_active_standby(self.inputs.compute_ips, pool_uuid)
        assert result, errmsg

        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        associated_vip = pool['vip_id']

        #Verify VIP list is updatedi after vip create
        vip_list = self.quantum_h.list_vips()
        if vip_list:
            errmsg = ("vip with id %s not present in vip list after vip create"
                      " vip list didnt get updated" % (lb_vip['id']))
            for vip in vip_list:
                if vip['id'] == lb_vip['id']:
                    self.logger.info("vip with id %s present in vip list after vip create"
                         % (lb_vip['id']))
                    break
                else:
                    assert False, errmsg

        #Delete the vip
        self.logger.info("deleting the vip associated with pool %s" % associated_vip)
        self.quantum_h.delete_vip(associated_vip)
        self.remove_method_from_cleanups((self.quantum_h.delete_vip, (associated_vip,), {}))

        #Verify netns and Haproxy got terminated after VIP delete and is
        #removed from API Server
        self.verify_on_vip_delete(pool_uuid, associated_vip)

        #Verify VIP list is updated after vip delete
        vip_list = self.quantum_h.list_vips()
        if vip_list:
            errmsg = ("vip with id %s still present in vip list even after vip delete"
                      " vip list didnt get updated" % (associated_vip))
            for vip in vip_list:
                if vip['id'] == associated_vip:
                    assert False, errmsg
        self.logger.info("vip with id %s not present in vip list after vip delete"
                         % (associated_vip))


        #Verfy if the pool is updated
        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        vip_associated = pool['vip_id']
        if vip_associated:
            errmsg = ("vip with id %s still shows as associated with pool,"
                      " even after vip delete. Pool is not geting updated"
                       % (vip_associated))
            assert False, errmsg

            self.logger.info("vip not present in pool with id %s after vip is deleted"
                             % pool['id'])

        # end test_vip_delete

    @preposttest_wrapper
    def test_healthmonitor_delete(self):
        '''Create Lbaas pool and healthmonitor  associate HM with pool
           Delete HM and verify HM gets deleted and the
           pool gets updated
        '''
        result = True
        vn_pool = get_random_name('vn_pool')
        vn_pool_subnets = ['10.1.1.0/24']

        vn_pool_fixture = self.create_vn(vn_pool, vn_pool_subnets)
        assert vn_pool_fixture.verify_on_setup(), "vn %s verification failed" % vn_pool

        pool_name = 'mypool'
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        hm_delay = 10
        hm_max_retries = 3
        hm_probe_type = 'HTTP'
        hm_timeout = 5

        #create lb pool
        self.logger.info("creating lb pool:%s" % (pool_name))
        lb_pool = self.create_lb_pool(pool_name, lb_method, protocol, vn_pool_fixture.vn_subnet_objs[0]['id'])
        assert lb_pool, "lb pool create failed"
        #api server verification
        assert self.verify_lb_pool_in_api_server(lb_pool['id']), \
               "API server verification failed for pool with pool id %s" % (lb_pool['id'])
        pool_uuid = lb_pool['id']

        #Create HM and assocuate with pool
        self.logger.info("creating healthmonitor")
        healthmonitor = self.create_health_monitor(hm_delay, hm_max_retries, hm_probe_type, hm_timeout)
        assert self.verify_healthmonitor_in_api_server(healthmonitor['id']), \
               "API server verification failed for healthmonitor with id %s" % (healthmonitor['id'])

        #Associate HM to pool
        self.logger.info("associating healthmonitor to pool %s" % (lb_pool['name']))
        self.associate_health_monitor(lb_pool['id'], healthmonitor['id'])

        #Check if Health monitor is associated with the pool
        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        if pool['health_monitors'][0] == healthmonitor['id']:
            self.logger.info("pool %s is associated with healthmonitor %s" % (lb_pool['name'],
                              pool['health_monitors']))
        else:
           assert False, ("pool %s is not associated with healthmonitor %s" %(lb_pool['name'],
                          healthmonitor['id']))

        #verify in API server whether HM is associated with pool
        self.logger.info("Verify in API server whether pool is associaed with Healthmonitor")
        result,msg = self.verify_healthmonitor_association_in_api_server(lb_pool['id'], healthmonitor['id'])
        assert result, msg

        #Verify HM list is updatedi after HM create
        HM_list = self.quantum_h.list_health_monitors()
        result = True
        if HM_list:
            errmsg = ("healthmonitor with id %s not present in healthmonitor list"
                      " after healthmonitor create, healthmonitor list didnt get"
                      "  updated" % (healthmonitor['id']))
            for HM in HM_list:
                if HM['id'] == healthmonitor['id']:
                    self.logger.info("healthmonitor with id %s present in healthmonitor list after"
                                     "healthmonitor create " % (healthmonitor['id']))
                    result = True
                    break
                else:
                    result = False
            assert result, errmsg

        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        associated_hm = pool['health_monitors']

        #Delete HM and verify HM list and associated pool gets updated
        self.logger.info("deleting the healthmonitor %s" % healthmonitor['id'])
        try:
            self.quantum_h.delete_health_monitor(healthmonitor['id'])
        except NeutronClientException, e:
            self.logger.debug("Execption: (%s) raised while deleting the HM, as we"
                             " tried to delete the HM in use" % (e))
            errmsg = 'Request Failed: internal server error while processing your request'
            if errmsg in e.message:
                self.logger.error("Delete Healthmonitor in use ended with 'internal server"
                                  " error' instead proper error msg should have been given."
                                  " Failing the test here")
                assert False, ("internal server error while deleting the Health monitor in use."
                               " Expected proper error msg")

        #Verify HM still exists
        HM_list = self.quantum_h.list_health_monitors()
        result = True
        if HM_list:
            errmsg = ("healthmonitor with id %s not present in healthmonitor list"
                      " after we tried to  delete healthmonitor in use"
                      % (healthmonitor['id']))
            for HM in HM_list:
                if HM['id'] == healthmonitor['id']:
                    self.logger.info("healthmonitor with id %s present in healthmonitor list"
                                      % (healthmonitor['id']))
                    result = True
                    break
                else:
                    result = False
                assert result, errmsg

        #Verfy if the pool still has the HM associated
        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        HM_associated = pool['health_monitors']
        if HM_associated[0] == healthmonitor['id']:
            self.logger.info("Healthmonitor with id %s is still associated with pool"
                              % healthmonitor['id'])
        else:
            errmsg = ("healthmonitor with id %s is not associated with pool,"
                      " after we tried to delete healthmonitor"
                       % (healthmonitor['id']))
            assert False, errmsg

    # end test_healthmonitor_delete
