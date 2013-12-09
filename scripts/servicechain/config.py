import time

import paramiko
import fixtures
from fabric.api import run, hide, settings

from vn_test import VNFixture
from vm_test import VMFixture
from policy_test import PolicyFixture
from floating_ip import FloatingIPFixture
from svc_instance_fixture import SvcInstanceFixture
from svc_template_fixture import SvcTemplateFixture
from connections import ContrailConnections
from policy.config import AttachPolicyFixture


class ConfigSvcChain(fixtures.TestWithFixtures):
    def delete_si_st(self, si_fixtures, st_fix):
        for si_fix in si_fixtures:
            self.logger.debug("Delete SI '%s'", si_fix.si_name)
            si_fix.cleanUp()
            self.remove_from_cleanups(si_fix)

        self.logger.debug("Delete ST '%s'", st_fix.st_name)
        st_fix.cleanUp()
        self.remove_from_cleanups(st_fix)

    def config_st_si(self, st_name, si_name_prefix, si_count,
            svc_scaling= False, max_inst= 1, domain='default-domain', project='admin', left_vn=None,
                     right_vn=None, svc_type='firewall', svc_mode='transparent', flavor= 'm1.medium'):
        if (svc_scaling == True and svc_mode != 'transparent'):
            if_list = [['management', False], ['left', True], ['right', False]]
        else:
            if_list = [['management', False], ['left', False], ['right', False]]

        if left_vn and right_vn:
            #In network/routed mode
            svc_img_name = "vsrx"
        elif left_vn:
            #Analyzer mode
            svc_img_name = "analyzer"
            if_list = [['left', False]]
        else:
            #Transperent/bridge mode
            svc_img_name = "vsrx-bridge"
        #create service template
        st_fixture = self.useFixture(SvcTemplateFixture(
            connections=self.connections, inputs=self.inputs, domain_name=domain,
            st_name=st_name, svc_img_name=svc_img_name, svc_type=svc_type,
            if_list=if_list, svc_mode=svc_mode, svc_scaling= svc_scaling, flavor= flavor))
        assert st_fixture.verify_on_setup()

        #create service instances
        si_fixtures = []
        for i in range(0, si_count):
            verify_vn_ri = True
            if i:
               verify_vn_ri = False
            si_name = si_name_prefix + str(i + 1)
            si_fixture = self.useFixture(SvcInstanceFixture(
                connections=self.connections, inputs=self.inputs,
                domain_name=domain, project_name=project, si_name=si_name,
                svc_template=st_fixture.st_obj, if_list=if_list,
                left_vn_name=left_vn, right_vn_name=right_vn, do_verify=verify_vn_ri, max_inst=max_inst))
            si_fixtures.append(si_fixture)

        return (st_fixture, si_fixtures)

    def chain_si(self, si_count, si_prefix):
        action_list = []
        for i in range(0, si_count):
            si_name = si_prefix + str(i + 1)
            #chain services by appending to action list
            si_fq_name = 'default-domain' + ':' + 'admin' + ':' + si_name
            action_list.append(si_fq_name)
        time.sleep(20)
        return action_list

    def config_policy(self, policy_name, rules):
        """Configures policy."""
        #create policy
        policy_fix = self.useFixture(PolicyFixture(
            policy_name=policy_name, rules_list=rules,
            inputs=self.inputs, connections=self.connections))
        return policy_fix

    def config_vn(self, vn_name, vn_net):
        vn_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn_name, inputs=self.inputs, subnets=vn_net))
        assert vn_fixture.verify_on_setup()
        return vn_fixture

    def attach_policy_to_vn(self, policy_fix, vn_fix, policy_type=None):
        policy_attach_fix = self.useFixture(AttachPolicyFixture(
            self.inputs, self.connections, vn_fix, policy_fix, policy_type))
        return policy_attach_fix

    def config_vm(self, vn_fix, vm_name):
        vm_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn_fix.obj, vm_name=vm_name, image_name='ubuntu-traffic', ram = '4096'))
        return vm_fixture

 
    def config_fip(self, vn_id, pool_name):
         fip_fixture = self.useFixture(FloatingIPFixture(
             project_name=self.inputs.project_name, inputs=self.inputs,
             connections=self.connections, pool_name=pool_name,
             vn_id=vn_id))
         return fip_fixture

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break

    def detach_policy(self, vn_policy_fix):
        self.logger.debug("Removing policy from '%s'", vn_policy_fix.vn_fixture.vn_name)
        vn_policy_fix.cleanUp()
        self.remove_from_cleanups(vn_policy_fix)

    def unconfig_policy(self, policy_fix):
        """Un Configures policy."""
        self.logger.debug("Delete policy '%s'", policy_fix.policy_name)
        policy_fix.cleanUp()
        self.remove_from_cleanups(policy_fix)

    def delete_vn(self, vn_fix):
        self.logger.debug("Delete vn '%s'", vn_fix.vn_name)
        vn_fix.cleanUp()
        self.remove_from_cleanups(vn_fix)

    def delete_vm(self, vm_fix):
        self.logger.debug("Delete vm '%s'", vm_fix.vm_name)
        vm_fix.cleanUp()
        self.remove_from_cleanups(vm_fix)

    def get_svm_obj(self, vm_name):
        for vm_obj in self.nova_fixture.get_vm_list():
            if vm_obj.name == vm_name:
                return vm_obj
        errmsg = "No VM named '%s' found in the compute" % vm_name
        self.logger.error(errmsg)
        assert False, errmsg

    def get_svm_compute(self, svm_name):
        svm_obj = self.get_svm_obj(svm_name)
        vm_nodeip = self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(svm_obj)]['host_ip']
        return self.inputs.host_data[vm_nodeip]

    def get_svm_tapintf(self, svm_name):
        svm_obj = self.get_svm_obj(svm_name)
        vm_nodeip = self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(svm_obj)]['host_ip']
        inspect_h = self.agent_inspect[vm_nodeip]
        return inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id)[0]['name']

    def get_svm_metadata_ip(self, svm_name):
        tap_intf = self.get_svm_tapintf(svm_name)
        tap_object = inspect_h.get_vna_intf_details(tap_intf['name'])
        return tap_object['mdata_ip_addr']
