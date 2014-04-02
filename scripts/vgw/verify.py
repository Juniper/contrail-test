from time import sleep
import fixtures
import testtools
import os
from connections import ContrailConnections
from contrail_test_init import *
from vn_test import *
from vm_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from floating_ip import *
from testresources import OptimisingTestSuite, TestResource

class VerifyVgwCases():

    def test_vgw_with_fip(self):

        vm_name1= 'VGW_VM1'
        fip_pool_name = 'some-pool1'
        result=True
  
        # Verification of VN
        assert self.res.vn_fixture_private.verify_on_setup()
        assert self.res.vn_fixture_dict[0].verify_on_setup()

        # Creation of VM and validation
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_obj= self.res.vn_fixture_private.obj, vm_name= vm_name1))
        assert vm1_fixture.verify_on_setup()

        # FIP Pool creation and validation 
        fip_fixture= self.useFixture(FloatingIPFixture( project_name= self.inputs.project_name, inputs = self.inputs, connections= self.connections, pool_name = fip_pool_name, vn_id= self.res.vn_fixture_dict[0].vn_id ))
        assert fip_fixture.verify_on_setup()

        # FIP pool association and validation 
        fip_id= fip_fixture.create_and_assoc_fip( self.res.vn_fixture_dict[0].vn_id, vm1_fixture.vm_id)
        assert fip_fixture.verify_fip( fip_id, vm1_fixture, self.res.vn_fixture_dict[0] )
        self.addCleanup( fip_fixture.disassoc_and_delete_fip, fip_id)

        self.logger.info( "Now trying to ping www-int.juniper.net")
        if not vm1_fixture.ping_with_certainty( 'www-int.juniper.net' ):
            result = result and False

        if not result:
            self.logger.error('Test  ping outside VN cluster from VM %s failed' %(vm1_name))
            assert result

        return True
    # End test_vgw_with_fip_on_same_node

