import test_v1
import re
from common.connections import ContrailConnections
from common import isolated_creds
from vm_test import VMFixture
from vn_test import VNFixture
from scripts.vm_regression import base as vm_base

class BaseVcenterGateway(vm_base.BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(BaseVcenterGateway, cls).setUpClass()
        if not cls.inputs.if_vcenter_gw_setup:
            inst = cls()
            raise inst.skipTest(
                "Skipping Test.vcenter gateway not enabled in the setup")
        cls.vcenter_orch = cls.connections.slave_orch
        cls.openstack_orch = cls.connections.orch
        cls.vcenter_orch.create_vn_vmi_for_stp_bpdu_to_be_flooded()
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseVcenterGateway, cls).tearDownClass()
    #end tearDownClass 


    def create_vn(self, *args, **kwargs):
        return self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections,
                          inputs=self.inputs,
                          *args, **kwargs
                          ))

    def create_vm(self, vn_fixture=None,vn_ids=[], image_name='ubuntu', *args, **kwargs):
        if vn_fixture:
            return self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_fixture.obj,
                    image_name=image_name,
                    *args, **kwargs
                    ))
        if vn_ids:
            return self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_ids=vn_ids,
                    image_name=image_name,
                    *args, **kwargs
                    ))
             

