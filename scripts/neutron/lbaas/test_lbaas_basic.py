import os
import datetime
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_random_name
from common.neutron.lbaas.base import BaseTestLbaas
import test
from time import sleep

class TestBasicLbaas(BaseTestLbaas):

    @classmethod
    def setUpClass(cls):
        super(TestBasicLbaas, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicLbaas, cls).tearDownClass()

    @test.attr(type=['sanity', 'suite1'])
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
                                          image_name='cirros')
        pool_vm2_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm2,
                                          image_name='cirros')
        pool_vm3_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm3,
                                          image_name='cirros')
        client_vm1_fixture = self.create_vm(vn_vip_fixture,vm_name=client_vm1,
                                          image_name='cirros')

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
        assert lb_member1, "lb member create failed"
        assert self.verify_member_in_api_server(lb_member1['id']), \
              "API server verification failed for member with id %s" % (lb_member1['id'])
        lb_member2 = self.create_lb_member(pool_vm2_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member2, "lb member create failed"
        assert self.verify_member_in_api_server(lb_member2['id']), \
              "API server verification failed for member with id %s" % (lb_member2['id'])
        lb_member3 = self.create_lb_member(pool_vm3_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member3, "lb member create failed"
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
        sleep(60)

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

    @test.attr(type=['sanity', 'suite1'])
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
        #vn_vip_fixture = self.create_vn(vn_vip, vn_vip_subnets)
        vn_vip_fixture = vn_pool_fixture
        assert vn_vip_fixture.verify_on_setup()
        pool_vm1_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm1,
                                          image_name='cirros')
        pool_vm2_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm2,
                                          image_name='cirros')
        pool_vm3_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm3,
                                          image_name='cirros')
        client_vm1_fixture = self.create_vm(vn_vip_fixture,vm_name=client_vm1,
                                          image_name='cirros')

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
        assert lb_member1, "lb member create failed"
        assert self.verify_member_in_api_server(lb_member1['id']), \
              "API server verification failed for member with id %s" % (lb_member1['id'])
        lb_member2 = self.create_lb_member(pool_vm2_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member2, "lb member create failed"
        assert self.verify_member_in_api_server(lb_member2['id']), \
              "API server verification failed for member with id %s" % (lb_member2['id'])
        lb_member3 = self.create_lb_member(pool_vm3_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member3, "lb member create failed"
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
        pool = self.quantum_h.get_lb_pool(lb_pool['id'])
        if pool['health_monitors'][0] == healthmonitor['id']:
            self.logger.info("pool %s is associated with healthmonitor %s" % (lb_pool['name'], pool['health_monitors']))
        else:
           assert False, "pool %s is not associated with healthmonitor %s" %(lb_pool['name'], healthmonitor['id'])

        #verify in API server whether HM is associated with pool
        self.logger.info("Verify in API server whether pool is associaed with Healthmonitor")
        result,msg = self.verify_healthmonitor_association_in_api_server(lb_pool['id'], healthmonitor['id'])
        assert result, msg

        #Start SimpleHTTPServer on port 80 on all lb pool servers
        self.start_simpleHTTPserver(lb_pool_servers)
        sleep(60)

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
        if pool_vm2_fixture.vm_ip in lb_response1:
            self.logger.info("client requests are getting forwarded to backend server %s" % (pool_vm2_fixture.vm_name))
        else:
            assert False, "client requests are not getting forwareded to server %s" % (pool_vm2_fixture.vm_name)

        #Lets bring down backend server pool_vm2_fixture and requests from client should not
        #get forwded to pool_vm2_fixture
        pool_vm2_fixture.vm_obj.stop()
        self.logger.info("Waiting for the VM to shutdown")
        sleep(40)
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
        pool_vm2_fixture.clear_local_ips()
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
            if pool_vm2_fixture.vm_ip in lb_response1:
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
