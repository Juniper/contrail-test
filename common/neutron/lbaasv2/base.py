from builtins import str
from builtins import range
from common.neutron.base import BaseNeutronTest
from lbaasv2_fixture import LBaasV2Fixture
from tcutils.util import *
from security_group import SecurityGroupFixture, get_secgrp_id_from_name

class BaseLBaaSTest(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(BaseLBaaSTest, cls).setUpClass()
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
                image_name='cirros-traffic')
            vm_fix_list.append(vm_fix)
        return (vn_fixture, vm_fix_list)
    # end  create_vn_and_its_vms

    def start_webservers(self, vm_fixtures):
        for vm in vm_fixtures:
            assert vm.wait_till_vm_is_up()
            vm.start_webserver(listen_port=80)

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
        secgrp_fixture = self.useFixture(SecurityGroupFixture(
            self.connections, self.inputs.domain_name, self.inputs.project_name,
            secgrp_name='vip_sg', secgrp_entries=rule,option='neutron'))
        result, msg = secgrp_fixture.verify_on_setup()
        assert result, msg
        return secgrp_fixture
    # end create_sg

    def get_default_sg(self):
        return SecurityGroupFixture(self.connections,
                                    self.inputs.domain_name,
                                    self.inputs.project_name,
                                    secgrp_name='default', option='neutron')

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
                orchestrator=self.inputs.orchestrator,
                **kwargs))
        return lbaas_fixture
    # end create_lbaas method

    def run_curl(self, vm, vip, port=80, https=False):
        response = ''
        result = False
        if https:
            cmds = "curl -i -k https://"+vip+":"+str(port)
        else:
            cmds = "curl -i "+vip+":"+str(port)
        result = vm.run_cmd_on_vm(cmds=[cmds])
        result = result[cmds].split('\r\n')
        if "200 OK" in result[0]:
            return (True, result[-1])
        else:
            self.logger.error("curl request to the VIP failed, with response %s", result)
            return (False, result[-1])

    @retry(tries=4, delay=5)
    def verify_lb_method(self, client_fix, servers_fix, vip_ip, lb_method='ROUND_ROBIN', port=80, https=False):
        '''
        Function to verify the Load balance method, by sending HTTP Traffic
        '''
        #Do wget on the VIP ip from the client, Lets do it 3 times
        lb_response1 = set([])
        result = ''
        output = ''
        for i in range (0,len(servers_fix)):
            try:
                result,output = self.run_curl(client_fix,vip_ip,port,https)
                if result:
                    lb_response1.add(output.strip('\r'))
                else:
                    self.logger.debug("connection to vip %s failed" % (vip_ip))
                    return False
            except Exception as e:
                return False

        if lb_method == "ROUND_ROBIN" and len(lb_response1) != len(servers_fix):
            self.logger.debug("In Round Robin, failed to get the response from all the server")
            return False

        # To check lb-method ROUND ROBIN lets do wget again 3 times
        lb_response2 = set([])
        for i in range (0,len(servers_fix)):
            try:
                result,output = self.run_curl(client_fix,vip_ip,port,https)
                if result:
                    lb_response2.add(output.strip('\r'))
                else:
                    self.logger.debug("connection to vip %s failed" % (vip_ip))
                    return False
            except Exception as e:
                return False

        errmsg = ("lb-method %s doesnt work as expcted, First time requests went to servers %s"
                  " subsequent requests went to servers %s" %(lb_method, lb_response1, lb_response2))
        if not lb_response1 == lb_response2:
            self.logger.error(errmsg)
            return False
        if lb_method == "SOURCE_IP" and len(lb_response1) > 1:
            self.logger.error(errmsg)
            return False
        self.logger.info("lb-method %s works as expected,First time requests went to servers %s"
                         " subsequent requests went to servers %s" % (lb_method, lb_response1, lb_response2))
        return True
    #end def verify_lb_method

#end BaseLBaaSTest class

