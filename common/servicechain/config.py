import time
import paramiko
import fixtures
from fabric.api import run, hide, settings
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import get_random_cidr
from tcutils.util import get_random_name
from tcutils.cfgparser import parse_cfg_file
from vn_test import VNFixture
from vm_test import VMFixture
from policy_test import PolicyFixture
from floating_ip import FloatingIPFixture
from svc_instance_fixture import SvcInstanceFixture
from svc_template_fixture import SvcTemplateFixture
from common.connections import ContrailConnections
from common.policy.config import AttachPolicyFixture
from tcutils.util import retry


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
                     svc_scaling=False, max_inst=1, domain='default-domain', project='admin', mgmt_vn=None, left_vn=None,
                     right_vn=None, svc_type='firewall', svc_mode='transparent', flavor='contrail_flavor_2cpu', static_route=[None, None, None], ordered_interfaces=True, svc_img_name=None, st_version=1):

        svc_type_props = {
            'firewall': {'in-network-nat': 'tiny_nat_fw',
                         'in-network': 'tiny_in_net',
                         'transparent': 'tiny_trans_fw',
                         },
            'analyzer': {'analyzer': 'analyzer'}
        }

        svc_mode_props = {
            'in-network-nat':   {'left': {'shared': True},
                                 'right': {'shared': False},
                                 },
            'in-network':       {'left': {'shared': True},
                                 'right': {'shared': True}
                                 },
            'transparent':      {'left': {'shared': True},
                                 'right': {'shared': True}
                                 }
        }

        mgmt_props = ['management', False, False]
        left_scaling = False
        right_scaling = False
        if svc_scaling:
            left_scaling = True
            right_scaling = svc_mode_props[svc_mode]['right']['shared']
        svc_img_name = svc_img_name or svc_type_props[svc_type][svc_mode]
        images_info = parse_cfg_file('configs/images.cfg')
        flavor = flavor or images_info[svc_img_name]['flavor']
        if_list = [mgmt_props,
                   ['left', left_scaling, bool(static_route[1])],
                   ['right', right_scaling, bool(static_route[2])],
                   ]
        if svc_type == 'analyzer':
            left_scaling = svc_mode_props[svc_mode]['left']['shared']
            if_list = [['left', left_scaling, bool(static_route[1])]]

        self.logger.debug('SI properties:'"\n"
                          'type: %s '"\n"
                          'mode: %s' "\n"
                          'image: %s' "\n"
                          'flavor: %s' "\n"
                          'intf_list: %s' % (svc_type, svc_mode, svc_img_name, flavor, if_list))
        # create service template
        st_fixture = self.useFixture(SvcTemplateFixture(
            connections=self.connections, inputs=self.inputs, domain_name=domain,
            st_name=st_name, svc_img_name=svc_img_name, svc_type=svc_type,
            if_list=if_list, svc_mode=svc_mode, svc_scaling=svc_scaling, flavor=flavor, ordered_interfaces=ordered_interfaces, version=st_version))
        assert st_fixture.verify_on_setup()

        # create service instances
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
                mgmt_vn_name=mgmt_vn, left_vn_name=left_vn, right_vn_name=right_vn, do_verify=verify_vn_ri, max_inst=max_inst, static_route=static_route))
            if st_version == 2:
                self.logger.debug('Launching SVM')
                if svc_mode == 'transparent':
                    self.trans_mgmt_vn_name = get_random_name('trans_mgmt_vn')
                    self.trans_mgmt_vn_subnets = [
                        get_random_cidr(af=self.inputs.get_af())]
                    self.trans_left_vn_name = get_random_name('trans_left_vn')
                    self.trans_left_vn_subnets = [
                        get_random_cidr(af=self.inputs.get_af())]
                    self.trans_right_vn_name = get_random_name(
                        'trans_right_vn')
                    self.trans_right_vn_subnets = [
                        get_random_cidr(af=self.inputs.get_af())]
                    self.trans_mgmt_vn_fixture = self.config_vn(
                        self.trans_mgmt_vn_name, self.trans_mgmt_vn_subnets)
                    self.trans_left_vn_fixture = self.config_vn(
                        self.trans_left_vn_name, self.trans_left_vn_subnets)
                    self.trans_right_vn_fixture = self.config_vn(
                        self.trans_right_vn_name, self.trans_right_vn_subnets)
                for i in range(max_inst):
                    svm_name = get_random_name("pt_svm" + str(i))
                    pt_name = get_random_name("port_tuple" + str(i))
                    if svc_mode == 'transparent':
                        svm_fixture = self.config_and_verify_vm(
                            svm_name, image_name=svc_img_name, vns=[self.trans_mgmt_vn_fixture, self.trans_left_vn_fixture, self.trans_right_vn_fixture], count=1, flavor='m1.large')
                    else:
                        svm_fixture = self.config_and_verify_vm(
                            svm_name, image_name=svc_img_name, vns=[self.mgmt_vn_fixture, self.vn1_fixture, self.vn2_fixture], count=1, flavor='m1.large')
                    si_fixture.add_port_tuple(svm_fixture, pt_name)
            si_fixture.verify_on_setup()
            si_fixtures.append(si_fixture)

        return (st_fixture, si_fixtures)

    def chain_si(self, si_count, si_prefix, project_name):
        action_list = []
        for i in range(0, si_count):
            si_name = si_prefix + str(i + 1)
            # chain services by appending to action list
            si_fq_name = 'default-domain' + ':' + project_name + ':' + si_name
            action_list.append(si_fq_name)
        return action_list

    def config_policy(self, policy_name, rules):
        """Configures policy."""
        # create policy
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

    def config_and_verify_vm(self, vm_name, vn_fix=None, image_name='ubuntu-traffic', vns=[], count=1, flavor='contrail_flavor_small'):
        if vns:
            vn_objs = [vn.obj for vn in vns]
            vm_fixture = self.config_vm(
                vm_name, vns=vn_objs, image_name=image_name, count=count,
                flavor=flavor)
        else:
            vm_fixture = self.config_vm(
                vm_name, vn_fix=vn_fix, image_name=image_name, count=count,
                flavor=flavor)
        assert vm_fixture.verify_on_setup(), 'VM verification failed'
        assert vm_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        return vm_fixture

    def config_vm(self, vm_name, vn_fix=None, node_name=None, image_name='ubuntu-traffic', flavor='contrail_flavor_small', vns=[], count=1):
        if vn_fix:
            vm_fixture = self.useFixture(VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn_fix.obj, vm_name=vm_name, node_name=node_name, image_name=image_name, flavor=flavor, count=count))
        elif vns:
            vm_fixture = self.useFixture(VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vm_name=vm_name, node_name=node_name, image_name=image_name, flavor=flavor, vn_objs=vns, count=count))

        return vm_fixture

    def config_fip(self, vn_id, pool_name):
        fip_fixture = self.useFixture(FloatingIPFixture(
            project_name=self.inputs.project_name, inputs=self.inputs,
            connections=self.connections, pool_name=pool_name,
            vn_id=vn_id))
        return fip_fixture

    def detach_policy(self, vn_policy_fix):
        self.logger.debug("Removing policy from '%s'",
                          vn_policy_fix.vn_fixture.vn_name)
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
        for vm_obj in self.nova_h.get_vm_list():
            if vm_obj.name == vm_name:
                return vm_obj
        errmsg = "No VM named '%s' found in the compute" % vm_name
        self.logger.error(errmsg)
        assert False, errmsg

    @retry(delay=10, tries=15)
    def is_svm_active(self, vm_name):
        vm_status = self.get_svm_obj(vm_name).status
        if vm_status == 'ACTIVE':
            self.logger.debug('SVM state is active')
            return True
        else:
            self.logger.warn('SVM %s is not yet active. Current state: %s' %
                             (vm_name, vm_status))
            return False

    def get_svm_compute(self, svm_name):
        svm_obj = self.get_svm_obj(svm_name)
        vm_nodeip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(svm_obj)]['host_ip']
        return self.inputs.host_data[vm_nodeip]

    def get_svm_tapintf(self, svm_name):
        self.is_svm_active(svm_name)
        svm_obj = self.get_svm_obj(svm_name)
        vm_nodeip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(svm_obj)]['host_ip']
        inspect_h = self.agent_inspect[vm_nodeip]
        self.logger.debug(
            "svm_obj:'%s' compute_ip:'%s' agent_inspect:'%s'", svm_obj.__dict__,
            vm_nodeip, inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id))
        return inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id)[0]['name']

    def get_bridge_svm_tapintf(self, svm_name, direction):
        self.is_svm_active(svm_name)
        svm_obj = self.get_svm_obj(svm_name)
        vm_nodeip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(svm_obj)]['host_ip']
        inspect_h = self.agent_inspect[vm_nodeip]
        self.logger.debug(
            "svm_obj:'%s' compute_ip:'%s' agent_inspect:'%s'", svm_obj.__dict__,
            vm_nodeip, inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id))
        tap_intf_list = []
        vn = 'svc-vn-' + direction
        vrf = ':'.join(self.inputs.project_fq_name) + ':' + vn + ':' + vn
        for entry in inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id):
            if entry['vrf_name'] == vrf:
                self.logger.debug(
                    'The %s tap-interface of %s is %s' %
                    (direction, svm_name, entry['name']))
                return entry['name']

    def get_svm_tapintf_of_vn(self, svm_name, vn):
        self.is_svm_active(svm_name)
        svm_obj = self.get_svm_obj(svm_name)
        vm_nodeip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(svm_obj)]['host_ip']
        inspect_h = self.agent_inspect[vm_nodeip]
        self.logger.debug(
            "svm_obj:'%s' compute_ip:'%s' agent_inspect:'%s'", svm_obj.__dict__,
            vm_nodeip, inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id))
        tap_intf_list = []
        for entry in inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id):
            if entry['vrf_name'] == vn.vrf_name:
                self.logger.debug(
                    'The tap interface corresponding to %s on %s is %s' %
                    (vn.vn_name, svm_name, entry['name']))
                return entry['name']

    def get_svm_metadata_ip(self, svm_name):
        tap_intf = self.get_svm_tapintf(svm_name)
        tap_object = inspect_h.get_vna_intf_details(tap_intf['name'])
        return tap_object['mdata_ip_addr']

    def start_tcpdump_on_intf(self, host, tapintf):
        session = ssh(host['host_ip'], host['username'], host['password'])
        cmd = 'tcpdump -nni %s -c 1 proto 1 > /tmp/%s_out.log 2>&1' % (
            tapintf, tapintf)
        execute_cmd(session, cmd, self.logger)
    # end start_tcpdump_on_intf

    def stop_tcpdump_on_intf(self, host, tapintf):
        session = ssh(host['host_ip'], host['username'], host['password'])
        self.logger.info('Waiting for tcpdump to complete')
        time.sleep(10)
        output_cmd = 'cat /tmp/%s_out.log' % tapintf
        out, err = execute_cmd_out(session, output_cmd, self.logger)
        return out
    # end stop_tcpdump_on_intf
