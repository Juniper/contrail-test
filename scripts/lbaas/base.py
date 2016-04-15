import test_v1
from common import isolated_creds

import os
import fixtures
import tcutils.wrappers
import time
from vn_test import VNFixture
from vm_test import VMFixture
from lbaasv2_fixture import LBaasV2Fixture
from ipam_test import IPAMFixture
from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture
from test import attr
from netaddr import IPNetwork
from common.policy import policy_test_utils
from tcutils.util import *
from common.neutron.base import BaseNeutronTest

class BaseLBaaSTest(BaseNeutronTest, test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseLBaaSTest, cls).setUpClass()
        cls.orch = cls.connections.orch
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseLBaaSTest, cls).tearDownClass()
    # end tearDownClass

    def create_vn_and_its_vms(self, no_of_vm=1):
        '''
        Functions to create a VN and multiple VMs for this VN
        Returns a tuple, with VNFixture and VMFixtures list
        '''
        vn_fixture = self.create_vn()
        vm_fix_list = []
        for num in range(no_of_vm):
            vm_fix = self.create_vm(vn_fixture,
                flavor='contrail_flavor_small', image_name='ubuntu')
            vm_fix_list.append(vm_fix)
        for vm in vm_fix_list:
            assert vm.wait_till_vm_is_up()
        vm.start_webserver(listen_port=80)
        return (vn_fixture, vm_fix_list)

    # end  create_vn_and_its_vms

    def create_lbaas(self, lb_name, network_id,
                        cleanup=True,
                        **kwargs):
        '''
        Function to create lbaas , by calling lbaas fixture
        '''
        lbaas_fixture = self.useFixture(
            LBaasV2Fixture(
                lb_name=lb_name,
                network_id=network_id,
                connections=self.connections,
                **kwargs))
        return lbaas_fixture
    # end create_lbaas method

    def run_wget(self, vm, vip):
        response = ''
        out = ''
        result = False
        with hide('everything'):
            with settings(host_string='%s@%s' % (self.inputs.username,vm.vm_node_ip),
                             password=self.inputs.password, warn_only=True,abort_on_prompts= False):
                cmd1 = 'sudo wget http://%s' % vip
                cmd2 = 'cat index.html'
                cmd3 = 'rm -rf index.html'
                result = run_fab_cmd_on_node(host_string = '%s@%s'%(vm.vm_username,vm.local_ip),
                                        password = vm.vm_password, cmd = cmd1, as_sudo=False)
                if result.count('200 OK'):
                    result = True
                    self.logger.info("connections to vip %s successful" % (vip))
                    response = run_fab_cmd_on_node(host_string = '%s@%s'%(vm.vm_username,vm.local_ip),
                                                  password = vm.vm_password, cmd = cmd2, as_sudo=False)
                    out = run_fab_cmd_on_node(host_string = '%s@%s'%(vm.vm_username,vm.local_ip),
                                              password = vm.vm_password, cmd = cmd3, as_sudo=False)
                    self.logger.info("Request went to server: %s" % (response))
                else:
                    self.logger.error("Error in response on connecting to vip %s. Error is %s" % (vip, result))
                    result = False
                return (result,response)
    #end run_wget

    def verify_lb_method(self, client_fix, servers_fix, vip_ip, lb_method='ROUND_ROBIN'):
        '''
        Function to verify the Load balance method, by sending HTTP Traffic
        '''
        #verify the reachability to fip_ip from client1
        retries = 0
        while not client_fix.ping_to_ip(vip_ip):
            if retries == 10:
                assert client_fix.ping_to_ip(vip_ip)
            else:
                retries += 1
                time.sleep(10)

        #Do wget on the VIP ip from the client, Lets do it 3 times
        lb_response1 = []
        result = ''
        output = ''
        for i in range (0,len(servers_fix)):
            result,output = self.run_wget(client_fix,vip_ip)
            if result:
                lb_response1.append(output.strip('\r'))
            else:
                errmsg = "connection to vip %s failed" % (vip_ip)
                assert result, errmsg

        # To check lb-method ROUND ROBIN lets do wget again 3 times
        lb_response2 = []
        for i in range (0,len(servers_fix)):
            result,output = self.run_wget(client_fix,vip_ip)
            if result:
                lb_response2.append(output.strip('\r'))
            else:
                errmsg = "connection to vip %s failed" % (vip_ip)
                assert result, errmsg

        errmsg = ("lb-method %s doesnt work as expcted, First time requests went to servers %s"
                  " subsequent requests went to servers %s" %(lb_method, lb_response1, lb_response2))
        if not lb_response1 == lb_response2:
            self.logger.error(errmsg)
            assert False, errmsg
        if lb_method == "SOURCE_IP":
            if lb_response1[1:] != lb_response1[:-1]:
                assert False, errmsg
        self.logger.info("lb-method %s works as expected,First time requests went to servers %s"
                         " subsequent requests went to servers %s" % (lb_method, lb_response1, lb_response2))
        return True

    #end def verify_lb_method

#end BaseLBaaSTest class

