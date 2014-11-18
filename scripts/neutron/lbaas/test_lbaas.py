import os
import fixtures
import testtools
import datetime

from vn_test import *
from vm_test import *
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import run_fab_cmd_on_node
from neutronclient.common.exceptions import NeutronClientException

from base import BaseTestLbaas
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
        assert lb_member, "lb memebr create failed"
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
        pool_list = self.quantum_fixture.list_lb_pools()
        assert pool_list, "failed to get the pool list"
        for pool in pool_list:
            pool_names.append(pool['name'])
        assert pool_name in pool_names, "pool %s is not present in the pool list" % (pool_name)

        vip_list = self.quantum_fixture.list_vips()
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
        assert lb_member1, "lb memebr create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member1['id']), \
              "API server verification failed for member with id %s" % (lb_member1['id'])
        lb_member2 = self.create_lb_member(pool_vm2_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member2, "lb memebr create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member2['id']), \
              "API server verification failed for member with id %s" % (lb_member2['id'])
        lb_member3 = self.create_lb_member(pool_vm3_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member3, "lb memebr create failed"
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
        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        if pool['pool']['health_monitors'][0] == healthmonitor['id']:
            self.logger.info("pool %s is associated with healthmonitor %s" % (lb_pool['name'], pool['pool']['health_monitors']))
        else:
           assert False, "pool %s is not associated with healthmonitor %s" %(lb_pool['name'], healthmonitor['id'])

        #verify in API server whether HM is associated with pool
        self.logger.info("Verify in API server whether pool is associaed with Healthmonitor")
        result,msg = self.verify_healthmonitor_association_in_api_server(lb_pool['id'], healthmonitor['id'])
        assert result, msg

        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        associated_vip = pool['pool']['vip_id']
        associated_members = pool['pool']['members']
        associated_hm = pool['pool']['health_monitors']

        #Try to delete the pool with VIP,members and HM associated
        self.logger.info("Try to delete the pool is use")
        try:
            self.quantum_fixture.delete_lb_pool(lb_pool['id'])
        except NeutronClientException, e:
            self.logger.debug("Execption: (%s) raised while deleting the pool, as we"
                             " tried to delete the pool in use" % (e))
            errmsg = 'Request Failed: internal server error while processing your request'
            if errmsg in e.message:
                self.logger.debug("Delete pool in use ended with 'internal server error'"
                                  "proper error message should have been given, failing the test")
                assert False, ("Internal server error while deleting the pool in use."
                               " Expected proper error msg here.")

        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        if not pool:
            assert False, ("Expected pool with id %s to be present.But could not get the pool details"
                           "  after we tried to delete this pool in use" % (lb_pool['id']))

        #Checking to see if VIP is not deleted with pool delete
        vip = self.quantum_fixture.show_vip(associated_vip)
        if vip:
            self.logger.info("Vip with id %s present. Pool delete did not initiate the vip delete."
                              % (associated_vip))
        else:
            assert False, ("Expected vip with id %s to be present.But could not get the vip details"
                           "  after we tried to delete associated pool %s"
                           % (associated_vip, lb_pool['id']))

        #Checking to see if pool delete did not delete the members
        for member_id in associated_members:
            member = self.quantum_fixture.show_lb_member(member_id)
            if member:
                self.logger.info("Member with id %s present. Pool delete did not initiate the delete of"
                                  " associated member" % member_id)
            else:
                assert False, ("Expected member with id %s to be present. But could not get the member"
                                " details, after we tried to deleted the associated pool %s"
                                % (member_id, lb_pool['id']))

        #Verify if the pool delete did not delete the HM
        health_monitor = self.quantum_fixture.get_health_monitor(associated_hm[0])
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
        assert lb_member1, "lb memebr create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member1['id']), \
              "API server verification failed for member with id %s" % (lb_member1['id'])
        lb_member2 = self.create_lb_member(pool_vm2_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member2, "lb memebr create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member2['id']), \
              "API server verification failed for member with id %s" % (lb_member2['id'])
        lb_member3 = self.create_lb_member(pool_vm3_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member3, "lb memebr create failed"
        #api server verification
        assert self.verify_member_in_api_server(lb_member3['id']), \
              "API server verification failed for member with id %s" % (lb_member3['id'])

        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        associated_members = pool['pool']['members']

        if lb_member2['id'] in associated_members:
            self.logger.info("member with id %s present in member list associated with pool"
                              % (lb_member2['id']))
        else:
            errmsg = ("member with id %s not present in member list associated with pool,"
                      " not continuing the test failing the test here" % (lb_member2['id']))
            assert False, errmsg
        member_list = self.quantum_fixture.list_lb_members()
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
        self.quantum_fixture.delete_lb_member(lb_member2['id'])
        self.remove_any_method_from_cleanups((self.quantum_fixture.delete_lb_member, (lb_member2['id'],), {}))

        #Verify in the API server if the member is deleted
        self.verify_on_member_delete(lb_member2['id'])

        #Verify the member list
        member_list = self.quantum_fixture.list_lb_members()
        errmsg = ("member with id %s still present in member list even after member delete"
                  " member list didnt get updated" % (lb_member2['id']))
        for member in member_list:
            if member['id'] == lb_member2['id']:
                assert False, errmsg
        self.logger.info("member with id %s not present in member list after member delete"
                         % (lb_member2['id']))

        #Verfy if the pool is updated
        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        members_associated = pool['pool']['members']
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

        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        associated_vip = pool['pool']['vip_id']

        #Verify VIP list is updatedi after vip create
        vip_list = self.quantum_fixture.list_vips()
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
        self.quantum_fixture.delete_vip(associated_vip)
        self.remove_any_method_from_cleanups((self.quantum_fixture.delete_vip, (associated_vip,), {}))

        #Verify netns and Haproxy got terminated after VIP delete and is
        #removed from API Server
        self.verify_on_vip_delete(pool_uuid, associated_vip)

        #Verify VIP list is updated after vip delete
        vip_list = self.quantum_fixture.list_vips()
        if vip_list:
            errmsg = ("vip with id %s still present in vip list even after vip delete"
                      " vip list didnt get updated" % (associated_vip))
            for vip in vip_list:
                if vip['id'] == associated_vip:
                    assert False, errmsg
        self.logger.info("vip with id %s not present in vip list after vip delete"
                         % (associated_vip))


        #Verfy if the pool is updated
        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        vip_associated = pool['pool']['vip_id']
        if vip_associated:
            errmsg = ("vip with id %s still shows as associated with pool,"
                      " even after vip delete. Pool is not geting updated"
                       % (vip_associated))
            assert False, errmsg

            self.logger.info("vip not present in pool with id %s after vip is deleted"
                             % pool['pool']['id'])

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
        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        if pool['pool']['health_monitors'][0] == healthmonitor['id']:
            self.logger.info("pool %s is associated with healthmonitor %s" % (lb_pool['name'],
                              pool['pool']['health_monitors']))
        else:
           assert False, ("pool %s is not associated with healthmonitor %s" %(lb_pool['name'],
                          healthmonitor['id']))

        #verify in API server whether HM is associated with pool
        self.logger.info("Verify in API server whether pool is associaed with Healthmonitor")
        result,msg = self.verify_healthmonitor_association_in_api_server(lb_pool['id'], healthmonitor['id'])
        assert result, msg

        #Verify HM list is updatedi after HM create
        HM_list = self.quantum_fixture.list_health_monitors()
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

        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        associated_hm = pool['pool']['health_monitors']

        #Delete HM and verify HM list and associated pool gets updated
        self.logger.info("deleting the healthmonitor %s" % healthmonitor['id'])
        try:
            self.quantum_fixture.delete_health_monitor(healthmonitor['id'])
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
        HM_list = self.quantum_fixture.list_health_monitors()
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
        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        HM_associated = pool['pool']['health_monitors']
        if HM_associated == healthmonitor['id']:
            self.logger.info("Healthmonitor with id %s is still associated with pool"
                              % healthmonitor['id'])
        else:
            errmsg = ("healthmonitor with id %s is not associated with pool,"
                      " after we tried to delete healthmonitor"
                       % (healthmonitor['id']))
            assert False, errmsg

    # end test_healthmonitor_delete

    @preposttest_wrapper
    def test_lbmethod_round_robin(self):
        '''Creates Lbaas pool with lb-method ROUND ROBIN, 3 members and vip
           Verify: lb-method ROUND ROBIN works as expected, fail otherwise
        '''

        vn_pool = get_random_name('vn_pool')
        vn_vip = get_random_name('vn_vip')
        vn_pool_subnets = ['10.1.1.0/24']
        vn_vip_subnets = ['20.1.1.0/24']
        pool_vm1 = get_random_name('server1')
        pool_vm2 = get_random_name('server2')
        pool_vm3 = get_random_name('server3')
        client_vm1 = get_random_name('client1')

        vn_pool_fixture = self.create_vn(vn_pool, vn_pool_subnets)
        assert vn_pool_fixture.verify_on_setup()
        vn_vip_fixture = self.create_vn(vn_vip, vn_vip_subnets)
        assert vn_vip_fixture.verify_on_setup()
        pool_vm1_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm2_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm2,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm3_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm3,
                flavor='contrail_flavor_small', image_name='ubuntu')
        client_vm1_fixture = self.create_vm(vn_vip_fixture,vm_name=client_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')

        lb_pool_servers = [pool_vm1_fixture, pool_vm2_fixture, pool_vm3_fixture]

        assert pool_vm1_fixture.wait_till_vm_is_up()
        assert pool_vm2_fixture.wait_till_vm_is_up()
        assert pool_vm3_fixture.wait_till_vm_is_up()
        assert client_vm1_fixture.wait_till_vm_is_up()

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

        #create lb member
        self.logger.info("creating lb member")
        lb_member1 = self.create_lb_member(pool_vm1_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member1, "lb memebr create failed"
        assert self.verify_member_in_api_server(lb_member1['id']), \
              "API server verification failed for member with id %s" % (lb_member1['id'])
        lb_member2 = self.create_lb_member(pool_vm2_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member2, "lb memebr create failed"
        assert self.verify_member_in_api_server(lb_member2['id']), \
              "API server verification failed for member with id %s" % (lb_member2['id'])
        lb_member3 = self.create_lb_member(pool_vm3_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member3, "lb memebr create failed"
        assert self.verify_member_in_api_server(lb_member3['id']), \
              "API server verification failed for member with id %s" % (lb_member3['id'])

        #create vip
        self.logger.info("creating lb vip:%s" % (vip_name))
        lb_vip = self.create_vip(vip_name, protocol, protocol_port, vn_vip_fixture.vn_subnet_objs[0]['id'], lb_pool['id'])
        assert lb_vip, "lb vip create failed"
        vip_ip = lb_vip['address']
        #api server verification
        assert self.verify_vip_in_api_server(lb_vip['id']), \
               "API server verification failed for vip with vip id %s" % (lb_vip['id'])
        #TODO : agent verification

        #Start SimpleHTTPServer on port 80 on all lb pool servers
        output = ''
        self.start_simpleHTTPserver(lb_pool_servers)

        #Do wget on the VIP ip from the client, Lets do it 3 times
        lb_response1 = []
        result = ''
        for i in range (0,3):
            result,output = self.run_wget(client_vm1_fixture,vip_ip)
            if result:
                lb_response1.append(output.strip('\r'))
            else:
                errmsg = "connection to vip %s failed" % (vip_ip)
                assert result, errmsg

        # To check lb-method ROUND ROBIN lets do wget again 3 times
        lb_response2 = []
        for i in range (0,3):
            result,output = self.run_wget(client_vm1_fixture,vip_ip)
            if result:
                lb_response2.append(output.strip('\r'))
            else:
                errmsg = "connection to vip %s failed" % (vip_ip)
                assert result, errmsg

        errmsg = ("lb-method ROUND ROBIN doesnt work as expcted, First time requests went to servers %s"
                  " subsequent requests went to servers %s" %(lb_response1, lb_response2))
        if not lb_response1 == lb_response2:
            self.logger.error(errmsg)
            assert False, errmsg
        self.logger.info("lb-method ROUND ROBIN works as expected,First time requests went to servers %s"
                         " subsequent requests went to servers %s" % (lb_response1, lb_response2))

    # end test_lbmethod_round_robin

    @preposttest_wrapper
    def test_active_standby_failover(self):
        '''Creates Lbaas pool with lb-method ROUND ROBIN, 3 members and vip
           Verifies in active standby mode traffic flows through only Active
           Stop Agent service and verify traffic shifts to stnadby
           Fail otherwise
        '''

        vn_pool = get_random_name('vn_pool')
        vn_vip = get_random_name('vn_vip')
        vn_pool_subnets = ['10.1.1.0/24']
        vn_vip_subnets = ['20.1.1.0/24']
        pool_vm1 = get_random_name('server1')
        pool_vm2 = get_random_name('server2')
        pool_vm3 = get_random_name('server3')
        client_vm1 = get_random_name('client1')
        client_vm2 = get_random_name('client2')

        vn_pool_fixture = self.create_vn(vn_pool, vn_pool_subnets)
        assert vn_pool_fixture.verify_on_setup()
        vn_vip_fixture = self.create_vn(vn_vip, vn_vip_subnets)
        assert vn_vip_fixture.verify_on_setup()
        pool_vm1_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm2_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm2,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm3_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm3,
                flavor='contrail_flavor_small', image_name='ubuntu')
        client_vm1_fixture = self.create_vm(vn_vip_fixture,vm_name=client_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')

        lb_pool_servers = [pool_vm1_fixture, pool_vm2_fixture, pool_vm3_fixture]

        assert pool_vm1_fixture.wait_till_vm_is_up()
        assert pool_vm2_fixture.wait_till_vm_is_up()
        assert pool_vm3_fixture.wait_till_vm_is_up()
        assert client_vm1_fixture.wait_till_vm_is_up()

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

        #create lb member
        self.logger.info("creating lb member")
        lb_member1 = self.create_lb_member(pool_vm1_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member1, "lb memebr create failed"
        assert self.verify_member_in_api_server(lb_member1['id']), \
              "API server verification failed for member with id %s" % (lb_member1['id'])
        lb_member2 = self.create_lb_member(pool_vm2_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member2, "lb memebr create failed"
        assert self.verify_member_in_api_server(lb_member2['id']), \
              "API server verification failed for member with id %s" % (lb_member2['id'])
        lb_member3 = self.create_lb_member(pool_vm3_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member3, "lb memebr create failed"
        assert self.verify_member_in_api_server(lb_member3['id']), \
              "API server verification failed for member with id %s" % (lb_member3['id'])

        #create vip
        self.logger.info("creating lb vip:%s" % (vip_name))
        lb_vip = self.create_vip(vip_name, protocol, protocol_port, vn_vip_fixture.vn_subnet_objs[0]['id'], lb_pool['id'])
        assert lb_vip, "lb vip create failed"
        vip_ip = lb_vip['address']
        #api server verification
        assert self.verify_vip_in_api_server(lb_vip['id']), \
               "API server verification failed for vip with vip id %s" % (lb_vip['id'])
        #TODO : agent verification

        #sleep for 10 sec for netns to get created
        sleep(10)

        #get the active and standby computes
        obj = self.api_s_inspect.get_lb_pool(pool_id=lb_pool['id'])
        si = self.api_s_inspect.get_cs_si(project= self.project.project_name, si=lb_pool['id'], refresh=True)
        domain,project,name = si['service-instance']['fq_name']
        si_name='%s:%s:%s'%(domain,project,name)
        si_ops = self.analytics_obj.get_svc_instance(self.inputs.collector_ips[0], project= self.project.project_name,
                                                      instance=si_name)
        for vm in si_ops['vm_list'] :
            if vm['ha'] == 'active: 200':
                active = vm['vr_name']
            if vm['ha'] == 'standby: 100':
                standby = vm['vr_name']
        self.logger.info("lbaas, active is: %s and stnadby is: %s" % (active, standby))

        left_int_active = self.get_netns_left_intf(self.inputs.compute_info[active],lb_pool['id'])
        left_int_standby = self.get_netns_left_intf(self.inputs.compute_info[standby],lb_pool['id'])

        #Start SimpleHTTPServer on port 80 on all lb pool servers
        self.start_simpleHTTPserver(lb_pool_servers)

        #start tcpdump on Active
        pcap_active,session_active = self.start_tcpdump(self.inputs.compute_info[active], left_int_active)
        #start tcpdump on stndby
        pcap_standby,session_standby = self.start_tcpdump(self.inputs.compute_info[standby], left_int_standby)

        #Do wget on the VIP ip from the client, Lets do it 3 times
        result = ''
        for i in range (0,3):
            result,output = self.run_wget(client_vm1_fixture,vip_ip)

        #stop tcpdump
        count_active = self.stop_tcpdump(session_active, pcap_active)
        count_standby = self.stop_tcpdump(session_standby, pcap_standby)

        if (count_active != 0) and (count_standby ==0):
            self.logger.info("traffic is flowing only through active %s" % (active))
        else:
            assert False, "traffic is flowing through standby %s, when active %s is present" % (standby, active)

        #Check if the client VM is runing on the same compute before stopping the agent service.
        if client_vm1_fixture.vm_node_ip == self.inputs.compute_info[active]:
            self.logger.info("clinet vm %s running on active compute, launching another client vm on standby"
                             " %s before stopping the agent in active %s" % (client_vm1_fixture, standby, active))
            client_vm2_fixture = self.create_vm(vn_vip_fixture,vm_name=client_vm2,
                    flavor='contrail_flavor_small', node_name=standby, image_name='ubuntu')
            assert client_vm2_fixture.wait_till_vm_is_up()
            client_vm_fixture = client_vm2_fixture
        else:
            client_vm_fixture = client_vm1_fixture

        #stop the agent service in agent and check if the failover scenario is working.
        self.logger.info("stopping the agent service in active: %s to check the failover scenario" % (active))
        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'stop')

        #start tcpdump on Active
        pcap_active,session_active = self.start_tcpdump(self.inputs.compute_info[active], left_int_active)
        #start tcpdump on stndby
        pcap_standby,session_standby = self.start_tcpdump(self.inputs.compute_info[standby], left_int_standby)

        #Do wget on the VIP ip from the client, Lets do it 3 times
        result = ''
        for i in range (0,3):
            result,output = self.run_wget(client_vm_fixture,vip_ip)

        #stop tcpdump
        count_active = self.stop_tcpdump(session_active, pcap_active)
        count_standby = self.stop_tcpdump(session_standby, pcap_standby)

        #start the agent service in agent and check if the failover scenario is working.
        self.logger.info("start the agent service back in active: %s" % (active))
        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'start')

        if (count_active == 0) and (count_standby !=0):
            self.logger.info("traffic is flowing only through standby %s, failover working" % (standby))
        else:
            assert False, "traffic is not flowing through standby %s \
                           when agent in Active is down,  failover not \
                           working" % (standby)

    # end test_active_standby_failover

    @preposttest_wrapper
    def test_healthmonitor(self):
        '''Creates Lbaas pool with lb-method ROUND ROBIN, 3 members and vip
           create the healthmonitor of type HTTP associate with the pool.
           bringdown one of the backend server and verify requests are not
           sent to that server and loadbalcing happens between the remaining backend servers
           which are active.
        '''

        vn_pool = get_random_name('vn_pool')
        vn_vip = get_random_name('vn_vip')
        vn_pool_subnets = ['10.1.1.0/24']
        vn_vip_subnets = ['20.1.1.0/24']
        pool_vm1 = get_random_name('server1')
        pool_vm2 = get_random_name('server2')
        pool_vm3 = get_random_name('server3')
        client_vm1 = get_random_name('client1')

        vn_pool_fixture = self.create_vn(vn_pool, vn_pool_subnets)
        assert vn_pool_fixture.verify_on_setup()
        vn_vip_fixture = self.create_vn(vn_vip, vn_vip_subnets)
        assert vn_vip_fixture.verify_on_setup()
        pool_vm1_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm2_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm2,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm3_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm3,
                flavor='contrail_flavor_small', image_name='ubuntu')
        client_vm1_fixture = self.create_vm(vn_vip_fixture,vm_name=client_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')

        lb_pool_servers = [pool_vm1_fixture, pool_vm2_fixture, pool_vm3_fixture]

        assert pool_vm1_fixture.wait_till_vm_is_up()
        assert pool_vm2_fixture.wait_till_vm_is_up()
        assert pool_vm3_fixture.wait_till_vm_is_up()
        assert client_vm1_fixture.wait_till_vm_is_up()

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

        #create lb member
        self.logger.info("creating lb member")
        lb_member1 = self.create_lb_member(pool_vm1_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member1, "lb memebr create failed"
        assert self.verify_member_in_api_server(lb_member1['id']), \
              "API server verification failed for member with id %s" % (lb_member1['id'])
        lb_member2 = self.create_lb_member(pool_vm2_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member2, "lb memebr create failed"
        assert self.verify_member_in_api_server(lb_member2['id']), \
              "API server verification failed for member with id %s" % (lb_member2['id'])
        lb_member3 = self.create_lb_member(pool_vm3_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member3, "lb memebr create failed"
        assert self.verify_member_in_api_server(lb_member3['id']), \
              "API server verification failed for member with id %s" % (lb_member3['id'])

        #create vip
        self.logger.info("creating lb vip:%s" % (vip_name))
        lb_vip = self.create_vip(vip_name, protocol, protocol_port, vn_vip_fixture.vn_subnet_objs[0]['id'], lb_pool['id'])
        assert lb_vip, "lb vip create failed"
        vip_ip = lb_vip['address']
        #api server verification
        assert self.verify_vip_in_api_server(lb_vip['id']), \
               "API server verification failed for vip with vip id %s" % (lb_vip['id'])
        #TODO : agent verification

        #create helathmonitor of type HTTP
        self.logger.info("creating healthmonitor")
        healthmonitor = self.create_health_monitor(hm_delay, hm_max_retries, hm_probe_type, hm_timeout)
        assert self.verify_healthmonitor_in_api_server(healthmonitor['id']), \
               "API server verification failed for healthmonitor with id %s" % (healthmonitor['id'])

        #Associate HM to pool
        self.logger.info("associating healthmonitor to pool %s" % (lb_pool['name']))
        self.associate_health_monitor(lb_pool['id'], healthmonitor['id'])

        #Check if Health monitor is associated with the pool
        pool = self.quantum_fixture.get_lb_pool(lb_pool['id'])
        if pool['pool']['health_monitors'][0] == healthmonitor['id']:
            self.logger.info("pool %s is associated with healthmonitor %s" % (lb_pool['name'], pool['pool']['health_monitors']))
        else:
           assert False, "pool %s is not associated with healthmonitor %s" %(lb_pool['name'], healthmonitor['id'])

        #verify in API server whether HM is associated with pool
        self.logger.info("Verify in API server whether pool is associaed with Healthmonitor")
        result,msg = self.verify_healthmonitor_association_in_api_server(lb_pool['id'], healthmonitor['id'])
        assert result, msg

        #Start SimpleHTTPServer on port 80 on all lb pool servers
        self.start_simpleHTTPserver(lb_pool_servers)

        #Do wget on the VIP ip from the client, Lets do it 3 times
        out = True
        lb_response1 = []
        for i in range (0,3):
            result,output = self.run_wget(client_vm1_fixture,vip_ip)
            if result:
                lb_response1.append(output.strip('\r'))
            else:
                assert False, ("Test pre condition failed, Error in response on connecting to vip,"
                                " failing the test here, Helathmonitor functionality not verified.")
        self.logger.info("requests went to servers: %s" % (lb_response1))

        #check if server2 is in lb_response1 before bringing it down to check HM functionality
        self.logger.info("Verififying if the client request gets forwarded to %s before bringing"
                         " it down to verify Healthmonitor functinality" % (pool_vm2_fixture.vm_name))
        if pool_vm2_fixture.vm_name in lb_response1:
            self.logger.info("client requests are getting forwarded to backend server %s" % (pool_vm2_fixture.vm_name))
        else:
            self.logger.info("client requests are not getting forwareded to server %s" % (pool_vm2_fixture.vm_name))

        #Lets bring down backend server pool_vm2_fixture and requests from client should not
        #get forwded to pool_vm2_fixture
        pool_vm2_fixture.vm_obj.stop()
        #ping to the stopped VM to make sure it has stopped.
        if pool_vm1_fixture.ping_with_certainty(pool_vm2_fixture.vm_ip, expectation=False):
            self.logger.info("ping to vm %s failed.VM %s is in shutoff state"
                              " continuing the test" % (pool_vm2_fixture.vm_name, pool_vm2_fixture.vm_name))
        else:
            assert False, ("vm %s stil in active state, HM functinality can not be verified.Stop the VM"
                            "and then continue the test. failing the test now"  % (pool_vm2_fixture.vm_name))

        #remove the stopped server from lb_pool_servers and start the simpleHTTPserver again
        lb_pool_servers.remove(pool_vm2_fixture)
        self.start_simpleHTTPserver(lb_pool_servers)

        lb_response1 = []
        for i in range (0,3):
            result,output = self.run_wget(client_vm1_fixture,vip_ip)
            if result:
                lb_response1.append(output.strip('\r'))
            else:
                assert False, ("Error in response on connecting to vip,even with Healthmonitor associated"
                                 " requests fron client tries to go to backend server which is down")
                out = False
        if out:
            self.logger.info("client requests are not getting forwarded to backend server: %s"
                              " requests went to servers: %s. healthmonitor working as expected"
                               % (pool_vm2_fixture.vm_name, lb_response1))

        #Bring up the server back again and healthmonitor should add the server back to pool and
        #client requets should start getting forwarded to this server again.
        pool_vm2_fixture.vm_obj.start()
        #sleep for 10 sec for the VM to come back to Active state.
        self.logger.info("waiting for the VM to come back to Active state")
        sleep(10)
        #ping to the VM to make sure it is in Active state.
        if pool_vm1_fixture.ping_with_certainty(pool_vm2_fixture.vm_ip):
            self.logger.info("ping to vm %s passed.VM %s is in Active state"
                              " continuing the test" % (pool_vm2_fixture.vm_name, pool_vm2_fixture.vm_name))
        else:
            assert False, ("vm %s stil in shtuoff state, HM functinality can not be verified. start the VM"
                            "and then continue the test. failing the test now"  % (pool_vm2_fixture.vm_name))

        #add server from lb_pool_servers and start the simpleHTTPserver again
        lb_pool_servers.append(pool_vm2_fixture)
        self.start_simpleHTTPserver(lb_pool_servers)

        maxduration = 300
        start = datetime.datetime.now()
        timedelta = datetime.timedelta(seconds=maxduration)
        maxtime = start + timedelta
        while maxtime >= datetime.datetime.now():
            lb_response1 = []
            #Do wget on the VIP ip from the client, Lets do it 3 times
            for i in range (0,3):
                result,output = self.run_wget(client_vm1_fixture,vip_ip)
                if result:
                    lb_response1.append(output.strip('\r'))
                else:
                    errmsg = "connection to vip %s failed" % (vip_ip)
                    assert result, errmsg
            self.logger.info("requests went to servers: %s" % (lb_response1))

            #check if server2 is in lb_response1
            if pool_vm2_fixture.vm_name in lb_response1:
                self.logger.info("client requests are getting forwarded to backend server %s"
                                 " HM functionality working as expected " % (pool_vm2_fixture.vm_name))
                out = True
                break
            else:
                out = False
                self.logger.warning("client requests are not getting forwareded to server %s"
                                 " after server is up again, requests should have got forwarded to %s"
                                 " retrying...."  % (pool_vm2_fixture.vm_name, pool_vm2_fixture.vm_name))

        if not out:
            assert out, ("Reached Max wait, waited for (%s secs), still the client requests are not getting"
                         " forwareded to server %s, HM functinality not working as expected"
                          % (maxduration, pool_vm2_fixture.vm_name))

    # end test_healthmonitor

    @preposttest_wrapper
    def test_lbaas_garbage_collector(self):
        '''Create 2 Lbaas pool and 2 vips
           Check for netns got created and haproxy running
           Restart the agent service in compute and verify garbage collector
           working as expected, fail otherwise
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

        pool_name = 'mypool'
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = 'myvip'

        #create lb pool
        self.logger.info("creating lb pool:%s" % pool_name)
        lb_pool = self.create_lb_pool(pool_name, lb_method, protocol, vn_pool_fixture.vn_subnet_objs[0]['id'])
        assert lb_pool, "lb pool create failed"
        #api server verification
        assert self.verify_lb_pool_in_api_server(lb_pool['id']), \
               "API server verification failed for pool with pool id %s" % (lb_pool['id'])

        #create vip
        self.logger.info("creating lb vip:%s" % vip_name)
        lb_vip = self.create_vip(vip_name, protocol, protocol_port, vn_vip_fixture.vn_subnet_objs[0]['id'], lb_pool['id'])
        assert lb_vip, "lb vip create failed"
        #api server verification
        assert self.verify_vip_in_api_server(lb_vip['id']), \
               "API server verification failed for vip with vip id %s" % (lb_vip['id'])
        #TODO : agent verification

        #sleep for 10 sec netns to get created
        sleep(10)

        #Check if nets ns got created and haproxy running in compute nodes after vip creation
        result,errmsg = self.verify_active_standby(self.inputs.compute_ips, lb_pool['id'])
        assert result, errmsg

        #Get the active and standby computes
        obj = self.api_s_inspect.get_lb_pool(pool_id=lb_pool['id'])
        si = self.api_s_inspect.get_cs_si(project= self.project.project_name, si=lb_pool['id'], refresh=True)
        domain,project,name = si['service-instance']['fq_name']
        si_name='%s:%s:%s'%(domain,project,name)
        si_ops = self.analytics_obj.get_svc_instance(self.inputs.collector_ips[0], project= self.project.project_name,
                                                      instance=si_name)
        for vm in si_ops['vm_list'] :
            if vm['ha'] == 'active: 200':
                active = vm['vr_name']
            if vm['ha'] == 'standby: 100':
                standby = vm['vr_name']
        self.logger.info("lbaas, active is: %s and stnadby is: %s for pool %s"
                         % (active, standby, lb_pool['name']))

        #Restart the agent service in Active and Standby
        self.logger.info("stop and start the agent service in active: %s and standby %s"
                         " to verify the garbage collector functionallity" % (active, standby))
        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'stop')
        self.start_stop_service(self.inputs.compute_info[standby], 'contrail-vrouter-agent', 'stop')
        sleep(5)
        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'start')
        self.start_stop_service(self.inputs.compute_info[standby], 'contrail-vrouter-agent', 'start')
        result, msg = self.verify_agent_process_active(active)
        if not result:
            self.logger.error("Agent process did not come to active state in compute %s"
                              " after process is started again. failing the test here" % (active))
        assert result, msg
        result, msg = self.verify_agent_process_active(standby)
        if not result:
            self.logger.error("Agent process did not come to active state in compute %s"
                              " after process is started again. failing the test here" % (standby))
        assert result, msg

        #Check if there are any stale net ns in compute due to agent restart
        self.logger.info("verifying after the agent restart there are any stale entris of net ns"
                         "and haproxy")
        result,errmsg = self.verify_active_standby(self.inputs.compute_ips, lb_pool['id'])
        if result:
            self.logger.info("Stale entries of NET NS and haproxy not found in compute."
                              "garbage collector working as expected")
        assert result, errmsg

        #Stop the agent process and delete the vip. Verify netns gets deleted and haproxy gets killed
        #after agent is started.
        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'stop')
        sleep(5)

        #Delete VIP while the agent is stopped
        self.quantum_fixture.delete_vip(lb_vip['id'])
        self.remove_any_method_from_cleanups((self.quantum_fixture.delete_vip, (lb_vip['id'],), {}))

        result, msg = self.verify_vip_delete(lb_vip['id'])
        assert result, msg

        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'start')
        result, msg = self.verify_agent_process_active(active)
        if not result:
            self.logger.error("Agent process did not come to active state in compute %s"
                              " after process is started again. failing the test here" % (active))
        assert result, msg

        maxduration = 300
        start = datetime.datetime.now()
        timedelta = datetime.timedelta(seconds=maxduration)
        maxtime = start + timedelta
        while maxtime >= datetime.datetime.now():
            result, msg = self.verify_netns_delete(self.inputs.compute_info[active], lb_pool['id'])
            if result:
                self.logger.info("NET NS got deleted with in the garbage collector timeout,"
                                 " which is 5 mins in agent")
                break
        if not result:
            self.logger.error("waited till gargabe collector timeout which is (%s sec) in agent"
                              "NET NS did not get deleted in compute %s with in this time"
                              % (maxduration, active))
            assert result, msg
    #end test_lbaas_garbage_collector
