import test
from tcutils.wrappers import preposttest_wrapper
from tcutils import gevent_lib
from tcutils.util import get_an_ip
from vnc_api.vnc_api import BadRequest
import vnc_api_test
from contrailapi import ContrailVncApi
from builtins import str
from builtins import range
import uuid
import random
from netaddr import *
from tcutils.util import skip_because, get_random_cidr, get_random_name
from common.contrail_fabric.base import BaseFabricTest
from common.base import GenericTestBase
from netaddr import IPNetwork, IPAddress
from vnc_api.vnc_api import *
from vm_test import VMFixture
from bms_fixture import BMSFixture

class SecurityGroup(BaseFabricTest):
	enterprise_style = True
	@preposttest_wrapper
	def test_security_group_bms(self):
                '''
		Description: Verify security group attached to BMS
		Test Steps:
                 Create two VN with BMS and VM as a part of each VN
		 Define security group rules with vn1 and vn2 subnets for TCP/UDP/ICMP
		 Create multiple security groups
		 Attach security groups to BMS
		 Verify different traffic scenarios based on rules defined
		 Delete security group attached to BMS
		 Update the rules defined and apply back the SG to BMS
                 Verify based on updated rules 
		Pass Criteria:Traffic should be verified based on rules defined
                '''
		self.inputs.set_af('dual')
		self.addCleanup(self.inputs.set_af, 'v4')
		vn1 = self.create_vn()
		vn2 = self.create_vn()
		bms_nodes = self.get_bms_nodes()
		bms1_vn1=bms_nodes[0]
		bms1_vn2=bms_nodes[1]
		bms2_vn1=bms_nodes[2]
		bms1 = self.create_bms(bms_name=bms1_vn1, vn_fixture=vn1, tor_port_vlan_tag=10)
		bms2 = self.create_bms(bms_name=bms1_vn2, vn_fixture=vn2, tor_port_vlan_tag=20)
		bms3 = self.create_bms(bms_name=bms2_vn1, vn_fixture=vn1, tor_port_vlan_tag=10)
		self.create_logical_router([vn1, vn2])
		vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros-traffic')
		vm2 = self.create_vm(vn_fixture=vn2, image_name='cirros-traffic')
		vm1.wait_till_vm_is_up()
		vm2.wait_till_vm_is_up()
		vm1_ip = vm1.get_vm_ips()[0]+'/32'
		vm2_ip = vm2.get_vm_ips()[0]+'/32'
		vn1_subnet = bms3.get_bms_ips()[0]+'/24'
		sg_rule_1 = self._get_secgrp_rule(protocol='tcp', dst_ports=(8004, 8006),
			                                        cidr=vm1_ip, direction='egress')
		sg_rule_2 = self._get_secgrp_rule(protocol='udp', dst_ports=(8004, 8006),
			                                        cidr=vm1_ip, direction='egress')
		sg_rule_3 = self._get_secgrp_rule(protocol='icmp',
								cidr=vm1_ip, direction='egress')
		sg_rule_4 = self._get_secgrp_rule(protocol='tcp', dst_ports=(8004, 8006),
			                                        cidr=vm2_ip, direction='egress')
		sg_rule_5 = self._get_secgrp_rule(protocol='tcp', dst_ports=(8004, 8006),
			                                        cidr=vn1_subnet, direction='egress')

		sg1 = self.create_security_group(rules=[sg_rule_1, sg_rule_2])
		sg2 = self.create_security_group(rules=[sg_rule_3])
		
		# Apply SG to BMS
		bms1.add_security_group([sg1.uuid, sg2.uuid])
    
                # TCP Traffic from bms1 to vm1 should pass
                # UDP Traffic from bms1 to vm1 should pass
                # Ping Traffic from bms1 to vm1 should pass
		# Ping Traffic from bms1 to vm2 should pass

                self.verify_traffic(bms1, vm1, 'tcp',
                                     sport=1111, dport=8006)
                self.verify_traffic(bms1, vm1, 'tcp',
                                     sport=1111, dport=8020, expectation=False)
                self.verify_traffic(bms1, vm1, 'udp',
                                     sport=1111, dport=8004)
                assert vm1.ping_with_certainty(ip=bms1.bms_ip)
                assert vm2.ping_with_certainty(ip=bms1.bms_ip,
                                    expectation=False)
                self.logger.info("Ping FAILED as expected")
		self.verify_traffic(bms1, bms2, 'tcp',
                                     sport=1111, dport=8006, expectation=False)

		#delete_security_group attached to BMS
		bms1.delete_security_group([sg1.uuid])

                #Create security group
                sg1 = self.create_security_group(rules=[sg_rule_1])
                #Update the rules
                sg1.replace_rules(rules=[sg_rule_1,sg_rule_2, sg_rule_4])

		# Apply back the updated SG to BMS
		bms1.add_security_group([sg1.uuid])
                
                self.verify_traffic(bms1, vm2, 'tcp',
                                     sport=1111, dport=8006)

		#Remove secuity group reference and delete SG attached to BMS
		bms1.delete_security_group([sg1.uuid, sg2.uuid])

class SPStyleSecurityGroup(SecurityGroup):
	enterprise_style = False
        @preposttest_wrapper
        def test_security_group_bms(self):
		vn1 = self.create_vn()
                vn2 = self.create_vn()
                self.create_logical_router([vn1, vn2])
		bms1_vn1=bms_nodes[0]
                bms1_vn2=bms_nodes[1]
                bms1_intf = self.inputs.bms_data[bms1_vn1]['interfaces'][:1]
                bms2_intf = self.inputs.bms_data[bms1_vn2]['interfaces'][1:]
                
		bms1 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               vlan_id=10, interfaces=bms1_intf)
                
		bms2 = self.create_bms(bms_name=bms, vn_fixture=vn2,
               tor_port_vlan_tag=20, interfaces=bms2_intf)
                self.do_ping_test(bms1, bms2.bms_ip)
                
		bms1_2 = self.create_bms(bms_name=bms, vn_fixture=vn2,
                tor_port_vlan_tag=30, interfaces=bms1_intf,
                bond_name=bms1.bond_name,
                port_group_name=bms1.port_group_name)
                
		self.do_ping_mesh([bms1, bms2, bms1_2])

                vn1_subnet = bms1.get_bms_ips()[0]+'/32'
		vn2_subnet = bms2.get_bms_ips()[0]+'/32'

                sg_rule_1 = self._get_secgrp_rule(protocol='tcp', dst_ports=(8004, 8006),
                                                                cidr=vn2_subnet, direction='egress')
                sg_rule_2 = self._get_secgrp_rule(protocol='udp', dst_ports=(8004, 8006),
                                                                cidr=vn2_subnet, direction='egress')
		sg_rule_3 = self._get_secgrp_rule(protocol='icmp',
                                                                cidr=vn1_subnet, direction='egress')

		sg1 = self.create_security_group(rules=[sg_rule_1, sg_rule_2])
                sg2 = self.create_security_group(rules=[sg_rule_3])


		bms1.add_security_group([sg1.uuid])
		bms1_2.add_security_group([sg2.uuid])

		self.verify_traffic(bms1, bms1_2, 'tcp',
                                     sport=1111, dport=8006)
                self.verify_traffic(bms1, bms1_2, 'tcp',
                                     sport=1111, dport=8020, expectation=False)
		assert bms1_2.ping_with_certainty(ip=bms1.bms_ip)


