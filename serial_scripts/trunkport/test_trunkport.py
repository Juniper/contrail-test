import test
from tcutils.wrappers import preposttest_wrapper
from common.trunkport.base import BaseTrunkportTest
from collections import OrderedDict as dict
from tcutils import gevent_lib
from tcutils.util import get_an_ip
from vnc_api.vnc_api import BadRequest

class TestTrunkPort(BaseTrunkportTest):
    @preposttest_wrapper
    def test_trunkport_agent_restart(self):
        vm1 = self.create_vm(vn_fixture=self.vns['parent'], image_name='ubuntu-traffic')
        vm2 = self.create_vm(vn_fixture=self.vns['parent'], image_name='ubuntu-traffic')
        subport1_vm1 = self.setup_vmi(vn_id=self.vns['subport1'].uuid)
        subport2_vm1 = self.setup_vmi(vn_id=self.vns['subport2'].uuid)
        subport1_vm2 = self.setup_vmi(vn_id=self.vns['subport1'].uuid)
        subport2_vm2 = self.setup_vmi(vn_id=self.vns['subport2'].uuid)
        subports = {subport1_vm1: 10, subport2_vm1: 20}
        self.check_vms_active([vm1, vm2])
        trunk1 = self.create_trunk(vm1, subports)
        trunk2 = self.create_trunk(vm2)
        trunk2.add_subports({subport1_vm2.uuid: 10, subport2_vm2.uuid: 20})
        trunk1.verify_on_setup()
        trunk2.verify_on_setup()
        self.check_vms_booted([vm1, vm2])
        vm1.setup_subintf('eth0', vlan=10, macaddr=subport1_vm1.mac_address)
        vm1.setup_subintf('eth0', vlan=20, macaddr=subport2_vm1.mac_address)
        vm2.setup_subintf('eth0', vlan=10, macaddr=subport1_vm2.mac_address)
        vm2.setup_subintf('eth0', vlan=20, macaddr=subport2_vm2.mac_address)
        assert vm1.ping_with_certainty(vm2.vm_ip)
        assert vm1.ping_with_certainty(subport1_vm2.get_ip_addresses()[0])
        assert vm1.ping_with_certainty(subport2_vm2.get_ip_addresses()[0])
        self.inputs.restart_container([vm1.vm_node_ip], 'agent')
        vm1.clear_local_ips()
        self.check_vms_booted([vm1])
        assert vm1.ping_with_certainty(vm2.vm_ip)
        assert vm1.ping_with_certainty(subport1_vm2.get_ip_addresses()[0])
        assert vm1.ping_with_certainty(subport2_vm2.get_ip_addresses()[0])
