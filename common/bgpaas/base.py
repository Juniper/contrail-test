import test_v1
from bgpaas_fixture import BGPaaSFixture
from vn_test import VNFixture
from vm_test import VMFixture
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import *
from contrailapi import ContrailVncApi
from common.base import GenericTestBase
from common.neutron.base import BaseNeutronTest
from common.svc_health_check.base import BaseHC
class BaseBGPaaS(BaseNeutronTest, BaseHC):

    @classmethod
    def setUpClass(cls):
        super(BaseBGPaaS, cls).setUpClass()
        cls.project_name = cls.inputs.project_name
        cls.quantum_h= cls.connections.quantum_h
        cls.orch = cls.connections.orch
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    #end setUpClass

    def create_bgpaas(self, bgpaas_shared='false',autonomous_system='64512',bgpaas_ip_address=None, address_families=['inet', 'inet6'], verify=True):
        '''
        Calls the BGPaaS Fixture to create the object
        '''
        bgpaas_fixture = self.useFixture(BGPaaSFixture(
                     connections=self.connections,
                     name=get_random_name(self.project_name),
                     bgpaas_shared=bgpaas_shared, autonomous_system=autonomous_system, bgpaas_ip_address=bgpaas_ip_address, address_families=address_families))
        if verify:
            bgpaas_fixture.verify_on_setup()
        return bgpaas_fixture
    #end create_bgpaas

    def config_bgp_on_vsrx(self, src_vm=None, dst_vm=None, bgp_ip=None, lo_ip=None, address_families=[], autonomous_system='64512', neighbors=[], bfd_enabled=True):
        '''
        Pass VRRP config to the vSRX
        '''
	cmdList = []
	cmdList.extend(('set routing-options router-id ' + str(lo_ip),'set routing-options autonomous-system ' + str(autonomous_system),
	'set protocols bgp group bgpaas local-address ' + str(bgp_ip)))
	for family in address_families:
	    cmdList.append('set protocols bgp group bgpaas family ' + str(family)+ ' unicast')
	for neighbor in neighbors:
	    cmdList.append('set protocols bgp group bgpaas neighbor ' + str(neighbor))
	cmdList.append('set protocols bgp group bgpaas peer-as ' + str(self.inputs.router_asn))
	if bfd_enabled:
	    cmdList.extend(('set protocols bgp group bgpaas bfd-liveness-detection minimum-interval 1000', 
	'set protocols bgp group bgpaas bfd-liveness-detection multiplier 3', 
	'set protocols bgp group bgpaas bfd-liveness-detection session-mode multihop',
	'deactivate protocols bgp group bgpaas bfd-liveness-detection')) #This will help to check if contrail is sending multihop BFD packets over port 4784
	cmdList.extend(('set protocols bgp group bgpaas type external', 'set protocols bgp group bgpaas multihop', 'set protocols bgp group bgpaas export export-to-bgp',
	'set protocols bgp group bgpaas hold-time 90', 'set policy-options policy-statement export-to-bgp term allow_local from protocol direct',
	'set policy-options policy-statement export-to-bgp term allow_local from protocol local',
	'set policy-options policy-statement export-to-bgp term allow_local from protocol static', 'set policy-options policy-statement export-to-bgp term allow_local then next-hop ' + str(bgp_ip),
	'set policy-options policy-statement export-to-bgp term allow_local then accept', 'set policy-options policy-statement export-to-bgp term deny_all then reject'	))
	cmd_string = (';').join(cmdList)
        result = self.set_config_via_netconf(src_vm, dst_vm,
            cmd_string,timeout=10, device='junos',hostkey_verify="False")
        return result
	

    def attach_vmi_to_bgpaas(self, vmi, bgpaas_fixture):
        '''
        Attach VMI to the BGPaaS object
        '''
	result = bgpaas_fixture.attach_vmi(vmi)
	return result

    def detach_vmi_from_bgpaas(self, vmi, bgpaas_fixture):
        '''
        Detach the VMI from the BGPaaS object
        '''
	result = bgpaas_fixture.detach_vmi(vmi)
	return result

    def attach_shc_to_bgpaas(self, shc, bgpaas_fixture):
        '''
        Attach the Health Check to the BGPaaS object
        '''
	result = bgpaas_fixture.attach_shc(shc.uuid)
	return result

    def detach_shc_from_bgpaas(self, shc, bgpaas_fixture):
        '''
        Detach the Health Check from the BGPaaS object
        '''
	result = bgpaas_fixture.detach_shc(shc.uuid)
	return result
