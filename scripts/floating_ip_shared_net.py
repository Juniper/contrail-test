import os
import fixtures
from connections import ContrailConnections
from contrail_test_init import *
from vn_test import *
from vm_test import *
from floating_ip import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from project_test import *

class SharedNetExternalRouter():

    def verify_fip_from_shared_network_in_demo_project(self):

        vm1_name = 'vm_public'
        fvn_name = 'public100'
        fip_pool_name = self.inputs.fip_pool_name
        fip_subnets = [self.inputs.fip_pool]

        api_server_port = self.inputs.api_server_port
        api_server_ip = self.inputs.cfgm_ip
        mx_rt = self.inputs.mx_rt
        public_ip_to_ping = '8.8.8.8'

        vn1_name = 'vn_private'
        vn1_subnets = ['11.1.1.0/24']

        self.project_fixture = self.useFixture(ProjectFixture(
                vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        self.logger.info(
                'Default SG to be edited for allow all on project: %s' %
                self.inputs.project_name)
        self.project_fixture.set_sec_group_for_allow_all(
                self.inputs.project_name, 'default')

        self.demo_proj_inputs = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name = 'demo', username=self.inputs.stack_user, password=self.inputs.stack_password, connections=self.connections))
        self.demo_proj_inputs.get_project_connections()

        fvn_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name, connections=self.connections,
                    vn_name=fvn_name, inputs=self.inputs, subnets=fip_subnets, router_asn=self.inputs.router_asn, rt_number=mx_rt, shared=True, router_external=True))

        fvn_fixture.verify_on_setup()

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name='demo', connections = self.demo_proj_inputs.project_connections,
                vn_name=vn1_name, inputs = self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()

        vn_obj = fvn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        vm2_fixture = self.useFixture(VMFixture(
                                      connections = self.demo_proj_inputs.project_connections,
                                      vn_obj=vn1_fixture.obj, vm_name='vm1_private', project_name='demo'))
        assert vm2_fixture.verify_on_setup()

        project_obj_demo = self.vnc_lib.project_read(
            fq_name=['default-domain', 'demo'])
        fip_fixture= self.useFixture(FloatingIPFixture( project_name= self.inputs.project_name, inputs = self.inputs,
                    connections= self.connections, pool_name='', vn_id= fvn_fixture.vn_id, option='neutron'))

        fip_id= fip_fixture.create_and_assoc_fip(fvn_fixture.vn_id, vm2_fixture.vm_id, project=project_obj_demo)
        self.addCleanup( fip_fixture.disassoc_and_delete_fip, fip_id)

        assert fip_fixture.verify_fip( fip_id, vm2_fixture, fvn_fixture)
        assert fip_fixture.verify_on_setup()

        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip, count='20' )
        assert vm2_fixture.ping_with_certainty(public_ip_to_ping )

        return True
