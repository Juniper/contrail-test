import test_v1, time
from lbaasv2_fixture import LBaasV2Fixture
from tcutils.util import *
from common.neutron.base import BaseNeutronTest
from security_group import SecurityGroupFixture, get_secgrp_id_from_name

class BaseLBaaSTest(BaseNeutronTest, test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseLBaaSTest, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseLBaaSTest, cls).tearDownClass()
    # end tearDownClass

    def is_test_applicable(self):
        if self.inputs.orchestrator.lower() != 'openstack':
            return (False, 'Skipping Test. Openstack required')
        if self.inputs.get_build_sku().lower()[0] < 'l':
            return (False, 'Skipping Test. LBaasV2 is supported only on liberty and up')
        return (True, None)

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

    def create_sg(self):
        self.sg_allow_tcp = 'sec_group_allow_tcp' + '_' + get_random_name()
        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        secgrp_fixture = self.useFixture(SecurityGroupFixture(self.inputs,
                                                              self.connections, self.inputs.domain_name, self.inputs.project_name,
                                                              secgrp_name='vip_sg', secgrp_entries=rule,option='neutron'))
        result, msg = secgrp_fixture.verify_on_setup()
        assert result, msg
        return secgrp_fixture
    # end create_sg

    def get_default_sg(self):
        return SecurityGroupFixture(self.inputs,
                                    self.connections, self.inputs.domain_name, self.inputs.project_name,
                                    secgrp_name='default',option='neutron')

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

    def run_curl(self, vm, vip, port=80):
        response = ''
        result = False
        cmds = "curl -i "+vip+":"+str(port)
        result = vm.run_cmd_on_vm(cmds=[cmds])
        result = result[cmds].split('\r\n')
        if "200 OK" in result[0]:
            return (True, result[-1])
        else:
            self.logger.error("curl request to the VIP failed, with response %s", result)
            return (False, result[-1])

    def verify_lb_method(self, client_fix, servers_fix, vip_ip, lb_method='ROUND_ROBIN', port=80):
        '''
        Function to verify the Load balance method, by sending HTTP Traffic
        '''

        #Do wget on the VIP ip from the client, Lets do it 3 times
        lb_response1 = set([])
        result = ''
        output = ''
        for i in range (0,len(servers_fix)):
            result,output = self.run_curl(client_fix,vip_ip,port)
            if result:
                lb_response1.add(output.strip('\r'))
            else:
                errmsg = "connection to vip %s failed" % (vip_ip)
                assert result, errmsg

        # To check lb-method ROUND ROBIN lets do wget again 3 times
        lb_response2 = set([])
        for i in range (0,len(servers_fix)):
            result,output = self.run_curl(client_fix,vip_ip,port)
            if result:
                lb_response2.add(output.strip('\r'))
            else:
                errmsg = "connection to vip %s failed" % (vip_ip)
                assert result, errmsg

        errmsg = ("lb-method %s doesnt work as expcted, First time requests went to servers %s"
                  " subsequent requests went to servers %s" %(lb_method, lb_response1, lb_response2))
        if not lb_response1 == lb_response2:
            self.logger.error(errmsg)
            assert False, errmsg
        if lb_method == "SOURCE_IP" and len(lb_response1) > 1:
            assert False, errmsg
        self.logger.info("lb-method %s works as expected,First time requests went to servers %s"
                         " subsequent requests went to servers %s" % (lb_method, lb_response1, lb_response2))
        return True

    #end def verify_lb_method

#end BaseLBaaSTest class

