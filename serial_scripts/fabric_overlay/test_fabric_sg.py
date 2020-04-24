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
from time import sleep

class TestFabricSecurityGroup(BaseFabricTest):
    enterprise_style = True
    @skip_because(bms=2)
    @preposttest_wrapper
    def test_security_group(self):
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
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros-traffic')
        vm2 = self.create_vm(vn_fixture=vn2, image_name='cirros-traffic')
        self.create_logical_router([vn1, vn2])
        #vm1.wait_till_vm_is_up()
        #vm2.wait_till_vm_is_up()

        vm1_ip = vm1.get_vm_ips()[0]+'/32'
        vm2_ip = vm2.get_vm_ips()[0]+'/32'
        vn1_subnet = vn1.get_cidrs()[0]

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
        sg2 = self.create_security_group(rules=[sg_rule_3, sg_rule_5])

        bms_nodes = self.get_bms_nodes()
        bms1_vn1=bms_nodes[0]
        bms1_vn2=bms_nodes[1]
        bms1 = self.create_bms(bms_name=bms1_vn1, vn_fixture=vn1, vlan_id=10)
        bms2 = self.create_bms(bms_name=bms1_vn2, vn_fixture=vn2, tor_port_vlan_tag=20)
        workloads = [vm1, vm2, bms1, bms2]
        if len(bms_nodes) > 2:
            workload3 = self.create_bms(bms_name=bms_nodes[2], vn_fixture=vn1, tor_port_vlan_tag=10)
        else:
            workload3 = self.create_vm(vn_fixture=vn1, image_name='cirros-traffic')
            workload3.wait_till_vm_is_up()
        workloads.append(workload3)

        self.do_ping_mesh(workloads)
        # Apply SG to BMS
        bms1.add_security_groups([sg1.uuid, sg2.uuid])
        sleep(60)
    
        # TCP Traffic from bms1 to vm1 should pass
        # UDP Traffic from bms1 to vm1 should pass
        # Ping Traffic from bms1 to vm1 should pass
        # Ping Traffic from bms1 to vm2 should pass
        assert vm2.ping_with_certainty(ip=bms1.bms_ip,
            expectation=False)
        assert vm1.ping_with_certainty(ip=bms1.bms_ip)
        self.verify_traffic(bms1, vm1, 'tcp', sport=1111, dport=8006)
        self.verify_traffic(bms1, vm1, 'tcp',
            sport=1111, dport=8020, expectation=False)
        self.verify_traffic(bms1, vm1, 'udp', sport=1111, dport=8004)
        self.verify_traffic(bms1, workload3, 'tcp', sport=1111, dport=8006)

        #delete one SG attached to BMS
        bms1.delete_security_groups([sg1.uuid])
        sleep(60)

        self.verify_traffic(bms1, vm1, 'tcp', sport=1111, dport=8006)
        self.verify_traffic(bms1, vm1, 'udp',
            sport=1111, dport=8004, expectation=False)
        assert vm1.ping_with_certainty(ip=bms1.bms_ip)

        #add one more SG to BMS
        bms1.add_security_groups([sg1.uuid])
        sleep(60)
        self.verify_traffic(bms1, vm1, 'tcp', sport=1111, dport=8006)
        self.verify_traffic(bms1, vm1, 'udp', sport=1111, dport=8004)
        assert vm1.ping_with_certainty(ip=bms1.bms_ip)
        self.verify_traffic(bms1, vm2, 'tcp',
            sport=1111, dport=8006, expectation=False)

        #Update the rules of SG
        sg1.replace_rules(rules=[sg_rule_1, sg_rule_2, sg_rule_4])

        sleep(60)
        assert vm1.ping_with_certainty(ip=bms1.bms_ip)
        self.verify_traffic(bms1, vm2, 'tcp', sport=1111, dport=8006)
        self.verify_traffic(bms1, vm1, 'tcp', sport=1111, dport=8006)
        self.verify_traffic(bms1, vm1, 'tcp',
            sport=1111, dport=8020, expectation=False)

        #Add same SG to multiple BMS
        bms2.add_security_groups([sg1.uuid])
        sleep(60)
        assert vm1.ping_with_certainty(ip=bms2.bms_ip, expectation=False)
        assert vm1.ping_with_certainty(ip=bms1.bms_ip)
        self.verify_traffic(bms1, workload3, 'tcp', sport=1111, dport=8006)
        self.verify_traffic(bms2, workload3, 'tcp',
            sport=1111, dport=8006, expectation=False)
        self.verify_traffic(bms1, workload3, 'tcp',
            sport=1111, dport=8000, expectation=False)
        self.verify_traffic(bms1, vm1, 'tcp', sport=1111, dport=8006)
        self.verify_traffic(bms2, vm1, 'tcp', sport=1111, dport=8004)

        #Remove all SGs attached to BMS
        bms1.delete_security_groups([sg1.uuid, sg2.uuid])
        sleep(60)
        assert vm1.ping_with_certainty(ip=bms1.bms_ip)
        assert vm1.ping_with_certainty(ip=bms2.bms_ip, expectation=False)
        self.verify_traffic(bms1, workload3, 'tcp', sport=1111, dport=8006)
        self.verify_traffic(bms2, workload3, 'tcp',
            sport=1111, dport=8006, expectation=False)
        self.verify_traffic(bms2, vm1, 'tcp', sport=1111, dport=8004)

class TestFabricSPStyleSecurityGroup(TestFabricSecurityGroup):
    enterprise_style = False
    @preposttest_wrapper
    def test_security_group_2(self):
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn2, image_name='cirros-traffic')
        self.create_logical_router([vn1, vn2])
        vn1_subnet = vn1.get_cidrs()[0]
        vn2_subnet = vn2.get_cidrs()[0]

        sg_rule_1 = self._get_secgrp_rule(protocol='tcp', dst_ports=(8004, 8006),
            cidr=vn2_subnet, direction='egress')
        sg_rule_2 = self._get_secgrp_rule(protocol='udp', dst_ports=(8004, 8006),
            cidr=vn2_subnet, direction='egress')
        sg_rule_3 = self._get_secgrp_rule(protocol='icmp', direction='egress')
        sg_rule_4 = self._get_secgrp_rule(protocol='udp', dst_ports=(0, 65535),
            cidr=vn1_subnet, direction='egress')

        sg1 = self.create_security_group(rules=[sg_rule_1, sg_rule_2])
        sg2 = self.create_security_group(rules=[sg_rule_3, sg_rule_4])

        bms = random.choice(self.get_bms_nodes())
        bms1 = self.create_bms(bms_name=bms, vn_fixture=vn1, vlan_id=10)
        bms2 = self.create_bms(bms_name=bms, vn_fixture=vn2,
            vlan_id=20, bond_name=bms1.bond_name,
            port_group_name=bms1.port_group_name)
        self.do_ping_mesh([vm1, bms1, bms2])

        bms1.add_security_groups([sg1.uuid])
        bms2.add_security_groups([sg2.uuid])
        sleep(60)

        self.verify_traffic(bms1, bms2, 'udp', sport=1111, dport=8006)
        self.verify_traffic(bms1, vm1, 'tcp', sport=1111, dport=8006)
        self.verify_traffic(bms1, bms2, 'tcp',
            sport=1111, dport=8006, expectation=False)
        assert bms1.ping_with_certainty(ip=vm1.vm_ip, expectation=False)
        assert bms2.ping_with_certainty(ip=vm1.vm_ip)
        assert bms2.ping_with_certainty(ip=bms1.bms_ip, expectation=False)

        bms1.delete_security_groups([sg1.uuid])
        sleep(60)
        assert bms2.ping_with_certainty(ip=bms1.bms_ip)
        self.verify_traffic(bms1, bms2, 'tcp',
            sport=1111, dport=8006, expectation=False)
        bms2.delete_security_groups([sg2.uuid])
        sleep(60)
        assert bms2.ping_with_certainty(ip=bms1.bms_ip)
        self.verify_traffic(bms1, bms2, 'tcp', sport=1111, dport=8006)
