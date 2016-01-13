import base
#from tcutils.topo.sdn_topo_setup import sdnTopoSetupFixture
#from sdn_topo_with_multi_project import *
import re
import time
import os
from contrail_fixtures import *
import fixtures
import testtools
import traceback
from vn_test import VNFixture
from vm_test import VMFixture
from quantum_test import QuantumHelper
from nova_test import NovaHelper
from floating_ip import FloatingIPFixture
from policy_test import PolicyFixture
from tcutils.commands import *
from fabric.context_managers import settings
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import *
from fabric.api import run
from fabric.state import connections
from scripts.securitygroup.config import ConfigSecGroup
import test
from OpenSSL.rand import status

class TestBackupRestore(base.BackupRestoreBaseTest, ConfigSecGroup):
    ''' backup and restore the configurations '''

    @classmethod
    def setUpClass(cls):
        super(TestBackupRestore, cls).setUpClass()
        cls.res.setUp(cls.inputs , cls.connections, cls.logger)
  
    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        super(TestBackupRestore, cls).tearDownClass()

    def runTest(self):
        pass
    #end runTest
    
    @test.attr(type=['backup'])
    @preposttest_wrapper
    def test_backup_restore(self):
        
        result = True
        
        status = self.check_traffic()
        assert status
        status = self.get_backup()
        if not status :
            return status
        #import pdb;pdb.trace()#-->break point before doing reimage
        #status=self.restore_backup()
        #if not status:
        #    return status
        #result=self.check_traffic()
        return result
        
    def get_backup(self):
        result = True
        backup_cmd = "cd /opt/contrail/utils;fab backup_data " 
        status = run(backup_cmd)
        self.logger.debug("LOG for fab backup_data command: %s" % status)
        assert not(status.return_code), 'Failed in running : cd /opt/contrail/utils;fab backup_data'
        result=result and status.return_code
        return result
    def restore_backup(self):
        result=True
        restore_cmd = "cd /opt/contrail/utils;fab restore_data " 
        status = run(restore_cmd)
        self.logger.debug("LOG for fab restore_data command: %s" % status)
        assert not(status.return_code), 'Failed in running : cd /opt/contrail/utils;fab restore_data'
        result=result and status.return_code
        return result
    
    
    def check_traffic(self):
        ''' Test to create policy, security group  and floating ip rules on common resources and checking if they work fine
        '''
        result = True
        vn11_vm3_fixture = self.res.vn11_vm3_fixture
        vn11_vm4_fixture = self.res.vn11_vm4_fixture

        assert self.res.verify_common_objects()
        '''
        # Ping between project1 and project2
        self.logger.info("Ping across projects with policy")
        src_vm_project1 = self.res.config_topo['project1']['vm']['vmc1']
        dst_vm_project2 = self.res.config_topo['project2']['vm']['vmc2']
        if not src_vm_project1.ping_to_ip(dst_vm_project2.vm_ip):
            result = result and False
            self.logger.error(
                'Ping acorss project failed with allowed policy and security group rule..\n')
            assert result, "ping failed across projects with policy"
        '''
        # Check security group for vn11_vm3 and vn11_vm4 first deny icmp then
        # allow it expect ping accordingly ####

        assert vn11_vm3_fixture.ping_with_certainty(vn11_vm4_fixture.vm_ip)
        assert vn11_vm4_fixture.ping_with_certainty(vn11_vm3_fixture.vm_ip)

        sec_grp_obj = self.vnc_lib.security_group_read(
            fq_name=[u'default-domain', self.inputs.project_name, 'default'])
        vn11_vm3_fixture.remove_security_group(secgrp=sec_grp_obj.uuid)
        vn11_vm4_fixture.remove_security_group(secgrp=sec_grp_obj.uuid)

        result = self.check_secgrp_traffic()
        assert result

        # checking traffic between common resource vm's by floating ip rule ###

        result = self.check_floatingip_traffic()
        assert result

        # Checking  Policy between vn11 and vn22  ######

        result = self.check_policy_traffic()
        assert result

        # Validate the service chaining in network  datapath ###

        for si_fix in self.res.si_fixtures:
            si_fix.verify_on_setup()

        assert self.res.vm1_fixture.ping_with_certainty(
            self.res.vm2_fixture.vm_ip)

        return result
    # end test_fiptraffic_before_upgrade
    
    
    # here check fip after upgrade method if required
    
    def check_secgrp_traffic(self):
        result = True
        vn11_vm3_fixture = self.res.vn11_vm3_fixture
        vn11_vm4_fixture = self.res.vn11_vm4_fixture

        self.sg1_name = 'sec_grp1'
        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '192.168.1.0', 'ip_prefix_len': 24}}, ],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '192.168.1.0', 'ip_prefix_len': 24}}, ],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]

        self.secgrp_fixture = self.config_sec_group(
            name=self.sg1_name, entries=rule)
        self.logger.info("Adding the sec groups to the VM's")
        vn11_vm3_fixture.add_security_group(secgrp=self.sg1_name)
        vn11_vm3_fixture.verify_security_group(self.sg1_name)
        vn11_vm4_fixture.add_security_group(secgrp=self.sg1_name)
        vn11_vm4_fixture.verify_security_group(self.sg1_name)

        # vn11_vm3 and vn11_vm4 are in sec_grp1  not allowing icmp traffic so
        # ping should fail ###
        self.logger.info("test for Security Group ")
        if vn11_vm3_fixture.ping_to_ip(vn11_vm4_fixture.vm_ip) or vn11_vm4_fixture.ping_to_ip(vn11_vm3_fixture.vm_ip):
            result = result and False
            self.logger.error(
                'Test to ping between VMs was  expected to FAIL problem with security group \n')
            assert result
        self.logger.info(
            "Ping test between vms  vn11_vm3  and vn11_vm4 was expected to fail since security group denies  'icmp' traffic")

        rule = [{'direction': '<>',
                'protocol': 'icmp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '192.168.1.0', 'ip_prefix_len': 24}}, ],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'icmp',
                 'src_addresses': [{'subnet': {'ip_prefix': '192.168.1.0', 'ip_prefix_len': 24}}, ],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]

        self.secgrp_fixture.replace_rules(rule)
        if not (vn11_vm3_fixture.ping_with_certainty(vn11_vm4_fixture.vm_ip) and vn11_vm4_fixture.ping_with_certainty(vn11_vm3_fixture.vm_ip)):
            result = result and False
            assert result, 'Failed in replacing security group rules to allow icmp traffic'
        vn11_vm3_fixture.remove_security_group(secgrp=self.sg1_name)
        vn11_vm4_fixture.remove_security_group(secgrp=self.sg1_name)

        return result

    def check_policy_traffic(self):

        result = True
        vn11_vm2_fixture = self.res.vn11_vm2_fixture
        vn22_vm2_fixture = self.res.vn22_vm2_fixture
        self.logger.info("Pinging from vn11_vm2 to vn22_vm2 by policy rule ")

        if not vn11_vm2_fixture.ping_with_certainty(vn22_vm2_fixture.vm_ip, expectation=True):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.info("Pinging from vn22_vm2 to vn11_vm2 by policy rule ")

        if not vn22_vm2_fixture.ping_with_certainty(vn11_vm2_fixture.vm_ip, expectation=True):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
        return result

    def check_floatingip_traffic(self):

        result = True
        vn11_fixture = self.res.vn11_fixture
        vn22_fixture = self.res.vn22_fixture
        fvn_fixture = self.res.fvn_fixture
        vn11_vm1_fixture = self.res.vn11_vm1_fixture
        vn22_vm1_fixture = self.res.vn22_vm1_fixture
        fvn_vm1_fixture = self.res.fvn_vm1_fixture
        fip_fixture = self.res.fip_fixture
        fip_id = self.res.fip_id
        fip_id1 = self.res.fip_id1
        self.logger.info('PINGING FROM VN11_VM1 TO VN22_VM1 \n')
        if not vn11_vm1_fixture.ping_with_certainty(fip_fixture.fip[fip_id1]):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.info('PINGING FROM VN11_VM1 TO FVN_VM1 \n')
        if not vn11_vm1_fixture.ping_to_ip(fvn_vm1_fixture.vm_ip):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.info('PINGING FROM VN22_VM1 TO FVN_VM1 \n')
        if not vn22_vm1_fixture.ping_to_ip(fvn_vm1_fixture.vm_ip):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        fip = vn11_vm1_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id).get_floating_ip_address()

        self.logger.info('PINGING FROM  FVN_VM1 to VN11_VM1 \n')
        if not fvn_vm1_fixture.ping_to_ip(fip):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
        return result


    
    