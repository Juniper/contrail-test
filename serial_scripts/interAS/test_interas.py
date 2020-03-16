from common.interAS.base import BaseInterAS
from builtins import str
from tcutils.wrappers import preposttest_wrapper
from common.neutron.base import BaseNeutronTest
from security_group import SecurityGroupFixture
import test
import time
from tcutils.util import *
from tcutils.tcpdump_utils import *
from common import isolated_creds
from test import attr

class TestInterAS(BaseInterAS):

    @preposttest_wrapper
    def test_interAS_controller_restart(self):
        self.inputs.restart_service('contrail-control',
            self.inputs.bgp_control_ips, container='control')
        self.verify_asbr_connection()
        assert self.verify_l3vpn_routing_instance()

    @preposttest_wrapper
    def test_interAS_ecmp_to_VM(self):
        self.ENCAP='udp'
        self.basic_end_to_end_ping(aap=True)

class TestInterASGRE(BaseInterAS):

    @preposttest_wrapper
    def test_interAS_ping_remote_ce(self):
        self.ENCAP='gre'
        self.basic_end_to_end_ping()

    @preposttest_wrapper
    def test_interAS_ping_with_subintf(self, ENCAP='gre'):
        self.config_encap_priority(ENCAP)
        self.tunnel_config_on_local_asbr(ENCAP)
        for router in self.inputs.remote_asbr_info:
            vn = {}
            vn['count']=2
            vn['vn1']={}
            vn['vn1']['subnet']=\
                self.inputs.remote_asbr_info[router]['subnet']
            vn['vn1']['asn']=\
                self.inputs.remote_asbr_info[router]['asn']
            vn['vn1']['target']=\
                self.inputs.remote_asbr_info[router]['target']

            vn['vn2']={}
            vn['vn2']['subnet']='10.10.10.0/24'
            vn_fixtures = self.setup_vns(vn)
    
            vmi = {'count': 2,
               'vmi1': {'vn': 'vn2'},
               'vmi2': {'vn': 'vn1','parent':'vmi1','vlan':20}
              }

            vmi_fixtures = self.setup_vmis(vn_fixtures, vmi)
            vm = {'count':1,
              'vm1':{'vn':['vn2'], 'vmi':['vmi1'], 'userdata':{ 
                  'vlan': str(vmi['vmi2']['vlan'])}}
            }
            vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm)
            gw_ip=vn['vn1']['subnet'].split('/')[0].replace('0','1',-1)
            cmd = ['ip route add default via %s dev eth0.20' %gw_ip]
            for vm_fix in vm_fixtures:
                vm_fixtures[vm_fix].run_cmd_on_vm(cmds=cmd, as_sudo=True, timeout=10)
                assert vm_fixtures[vm_fix].ping_with_certainty\
                  (ip=self.inputs.remote_asbr_info[router]['CE'][0])

    @preposttest_wrapper
    def test_interAS_vrouter_restart(self):
        self.ENCAP='gre'
        self.inputs.restart_service('contrail-vrouter',
            self.inputs.compute_ips, container='agent')
        assert self.verify_inet3_routing_instance()
        self.basic_end_to_end_ping()

class TestInterASUDP(TestInterASGRE):

    @preposttest_wrapper
    def test_interAS_ping_remote_ce(self):
        self.ENCAP = 'udp'
        self.basic_end_to_end_ping()

    @preposttest_wrapper
    def test_interAS_tcp_remote_ce(self):
        self.ENCAP = 'udp'
        self.basic_end_to_end_ping(verify_ssh=True)

    @preposttest_wrapper
    def test_interAS_ping_remote_with_fat_flow(self):
        self.ENCAP = 'udp'
        self.basic_end_to_end_ping(enable_fat_flow=True)

    @preposttest_wrapper
    def test_interAS_ping_with_subintf(self):
        self.ENCAP = 'udp'
        super(TestInterASUDP,self).test_interAS_ping_with_subintf(ENCAP='udp')

    @preposttest_wrapper
    def test_interAS_vrouter_restart(self):
        self.ENCAP='udp'
        self.inputs.restart_service('contrail-vrouter',
            self.inputs.compute_ips, container='agent')
        assert self.verify_inet3_routing_instance()
        self.basic_end_to_end_ping()

    @preposttest_wrapper
    def test_interAS_forwarding_mode(self):
        self.ENCAP = 'udp'
        self.basic_end_to_end_ping(forwarding_mode='l3')

