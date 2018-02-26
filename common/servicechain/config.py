import os
import time
import random

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
from tcutils.util import retry, is_v6
import random
import re

# Default images for vcenter based environments
VC_SVC_TYPE_PROPS = {
    'firewall': {'in-network-nat': 'ubuntu-nat-fw',
                 'in-network': 'ubuntu-in-net',
                 'transparent': '',
                 },
    'analyzer': {'transparent': 'analyzer',
                 'in-network' : 'analyzer',
                 }
}

SVC_TYPE_PROPS = {
    'firewall': {'in-network-nat': 'tiny_nat_fw',
                 'in-network': 'tiny_in_net',
                 'transparent': 'tiny_trans_fw',
                 },
    'analyzer': {'transparent': 'ubuntu',
                 'in-network' : 'ubuntu',
                 }
}

# To check what kind of intfs need to be configured for a image
SVC_IMAGE_PROPS = {
    'ubuntu' : { 'management' : False, 'left' : True, 'right' : False }
}

class ConfigSvcChain(fixtures.Fixture):

    def __init__(self, use_vnc_api=False, connections=None):
        self.use_vnc_api = use_vnc_api
        if connections:
            self.connections = connections
            self.inputs = connections.inputs
            self.orch = connections.orch
            self.vnc_lib = connections.vnc_lib
            self.logger = connections.logger
        super(ConfigSvcChain, self).__init__()

    def delete_si_st(self, si_fixtures, st_fix):
        for si_fix in si_fixtures:
            self.logger.debug("Delete SI '%s'", si_fix.si_name)
            si_fix.cleanUp()
            self.remove_from_cleanups(si_fix.cleanUp)

        self.logger.debug("Delete ST '%s'", st_fix.st_name)
        st_fix.cleanUp()
        self.remove_from_cleanups(st_fix.cleanUp)

    def config_st(self,
                  st_name,
                  mgmt=None,
                  left=None,
                  right=None,
                  st_version=2,
                  service_mode='transparent',
                  service_type='firewall'):
        '''
        mgmt, left, right are VN fq name strings
        '''
        if_details = {}
        if mgmt:
            if_details['management'] = {}
        if left:
            if_details['left'] = {}
        if right:
            if_details['right'] = {}

        st_fixture = self.useFixture(SvcTemplateFixture(
            connections=self.connections,
            st_name=st_name, service_type=service_type,
            if_details=if_details, service_mode=service_mode, version=st_version))
        assert st_fixture.verify_on_setup()
        return st_fixture
    # end config_st


    def config_sis(self,
                   si_name,
                   st_fixture,
                   si_count=1,
                   **kwargs):
        si_fixtures = []
        for index in range(si_count):
            si_fixture = self.config_si(si_name, st_fixture, **kwargs)
            si_fixtures.append(si_fixture)
        return si_fixtures


    def config_si(self,
                  si_name,
                  st_fixture,
                  mgmt_vn_fq_name=None,
                  left_vn_fq_name=None,
                  right_vn_fq_name=None,
                  port_tuples_props=None,
                  svm_fixtures=None,
                  static_route=None,
                  max_inst=1):
        si_name = si_name or get_random_name('si')
        if_details = {
            'management' : {'vn_name' : mgmt_vn_fq_name},
            'left' : {'vn_name' : left_vn_fq_name},
            'right': {'vn_name': right_vn_fq_name}
        }
        if svm_fixtures:
            port_tuples_props = port_tuples_props or []
            for svm in svm_fixtures:
                svm_pt_props = {}
                if mgmt_vn_fq_name:
                    svm_pt_props['management'] = svm.vmi_ids[mgmt_vn_fq_name]
                if left_vn_fq_name:
                    svm_pt_props['left'] = svm.vmi_ids[left_vn_fq_name]
                if right_vn_fq_name:
                    svm_pt_props['right'] = svm.vmi_ids[right_vn_fq_name]
                svm_pt_props['name'] = get_random_name("port_tuple")
                port_tuples_props.append(svm_pt_props)

        si_fixture = self.useFixture(SvcInstanceFixture(
            connections=self.connections,
            si_name=si_name,
            svc_template=st_fixture.st_obj,
            if_details=if_details,
            max_inst=max_inst,
            port_tuples_props=port_tuples_props,
            static_route=static_route))
        return si_fixture
    # end config_si

    def config_policy(self, policy_name, rules):
        """Configures policy."""
        use_vnc_api = getattr(self, 'use_vnc_api', None)
        # create policy
        policy_fix = self.useFixture(PolicyFixture(
            policy_name=policy_name, rules_list=rules,
            inputs=self.inputs, connections=self.connections,
            api=use_vnc_api))
        return policy_fix

    def config_vn(self, vn_name, vn_net, **kwargs):
        vn_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn_name, inputs=self.inputs, subnets=vn_net, **kwargs))
        assert vn_fixture.verify_on_setup()
        return vn_fixture

    def attach_policy_to_vn(self, policy_fix, vn_fix, policy_type=None):
        policy_attach_fix = self.useFixture(AttachPolicyFixture(
            self.inputs, self.connections, vn_fix, policy_fix, policy_type))
        return policy_attach_fix

    def config_vm_only(self,
                       vm_name,
                       vn_fix=None,
                       image_name='ubuntu-traffic',
                       vns=[],
                       count=1,
                       flavor='contrail_flavor_small',
                       zone=None,
                       node_name=None):
        if vns:
            vn_objs = [vn.obj for vn in vns if vn is not None]
            vm_fixture = self.config_vm(
                vm_name, vns=vn_objs, image_name=image_name, count=count,
                flavor=flavor, zone=zone, node_name=node_name)
        else:
            vm_fixture = self.config_vm(
                vm_name, vn_fix=vn_fix, image_name=image_name, count=count,
                flavor=flavor, zone=zone, node_name=node_name)
        return vm_fixture
    # end config_vm_only

    def verify_vms(self, vm_fixtures):
        for vm in vm_fixtures:
            self.verify_vm(vm)
    # end verify_vms

    def verify_vm(self, vm_fixture):
        assert vm_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
    # end verify_vm

    def config_and_verify_vm(self, *args, **kwargs):
        vm_fixture = self.config_vm_only(*args, **kwargs)
        self.verify_vm(vm_fixture)
        return vm_fixture
    # end config_and_verify_vm

    def config_vm(self,
                  vm_name,
                  vn_fix=None,
                  node_name=None,
                  image_name='ubuntu-traffic',
                  flavor='contrail_flavor_small',
                  vns=[],
                  count=1,
                  zone=None):
        if vn_fix:
            vm_fixture = self.useFixture(VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn_fix.obj, vm_name=vm_name, node_name=node_name,
                image_name=image_name, flavor=flavor, count=count, zone=zone))
        elif vns:
            vm_fixture = self.useFixture(VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vm_name=vm_name, node_name=node_name, image_name=image_name,
                flavor=flavor, vn_objs=vns, count=count, zone=zone))

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
        self.remove_from_cleanups(vn_policy_fix.cleanUp)

    def unconfig_policy(self, policy_fix):
        """Un Configures policy."""
        self.logger.debug("Delete policy '%s'", policy_fix.policy_name)
        policy_fix.cleanUp()
        self.remove_from_cleanups(policy_fix.cleanUp)

    def delete_vn(self, vn_fix):
        self.logger.debug("Delete vn '%s'", vn_fix.vn_name)
        vn_fix.cleanUp()
        self.remove_from_cleanups(vn_fix.cleanUp)

    def delete_vm(self, vm_fix):
        self.logger.debug("Delete vm '%s'", vm_fix.vm_name)
        vm_fix.cleanUp()
        self.remove_from_cleanups(vm_fix.cleanUp)

    def get_svm_obj(self, vm_name):
        for vm_obj in self.orch.get_vm_list():
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
            self.orch.get_host_of_vm(svm_obj)]['host_ip']
        return self.inputs.host_data[vm_nodeip]

    def get_svm_tapintf(self, svm_name):
        self.is_svm_active(svm_name)
        svm_obj = self.get_svm_obj(svm_name)
        vm_nodeip = self.inputs.host_data[
            self.orch.get_host_of_vm(svm_obj)]['host_ip']
        inspect_h = self.agent_inspect[vm_nodeip]
        self.logger.debug(
            "svm_obj:'%s' compute_ip:'%s' agent_inspect:'%s'", svm_obj.__dict__,
            vm_nodeip, inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id))
        tap_intfs = inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id)
        for tap_intf in tap_intfs:
            if 'tap' not in tap_intf['name']:
                tap_intfs.remove(tap_intf)
        return tap_intfs[0]['name']

    def get_bridge_svm_tapintf(self, svm_name, direction):
        vrf_name = self.get_svc_bridge_vrf(direction)
        return self.get_svm_tap_intf_by_vrf(svm_name, vrf_name)

    def get_svc_bridge_vrf(self, direction):
        vn = 'svc-vn-' + direction
        vrf = ':'.join(self.inputs.project_fq_name) + ':' + vn + ':' + vn

    def get_svm_tap_intf_by_vrf(self, svm_name, vrf_name):
        self.is_svm_active(svm_name)
        svm_obj = self.get_svm_obj(svm_name)
        vm_nodeip = self.inputs.host_data[
            self.orch.get_host_of_vm(svm_obj)]['host_ip']
        inspect_h = self.agent_inspect[vm_nodeip]
        self.logger.debug(
            "svm_obj:'%s' compute_ip:'%s' agent_inspect:'%s'", svm_obj.__dict__,
            vm_nodeip, inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id))
        tap_intf_list = []
        for entry in inspect_h.get_vna_tap_interface_by_vm(vm_id=svm_obj.id):
            if entry['vrf_name'] == vrf_name:
                self.logger.debug(
                    'The tap interface corresponding to vrf %s on %s is %s' %
                    (vrf_name, svm_name, entry['name']))
                return entry['name']
    # end get_svm_tap_intf_by_vrf


    def get_svm_tapintf_of_vn(self, svm_name, vn):
        return self.get_svm_tap_intf_by_vrf(svm_name, vn_vrf_name)

    def get_svm_metadata_ip(self, svm_name):
        tap_intf = self.get_svm_tapintf(svm_name)
        tap_object = inspect_h.get_vna_intf_details(tap_intf['name'])
        return tap_object['mdata_ip_addr']

    def start_tcpdump_on_intf(self, host, tapintf):
        session = ssh(host['host_ip'], host['username'], host['password'])
        cmd = 'sudo tcpdump -nni %s -c 1 proto 1 > /tmp/%s_out.log 2>&1' % (
            tapintf, tapintf)
        execute_cmd(session, cmd, self.logger)
    # end start_tcpdump_on_intf

    def stop_tcpdump_on_intf(self, host, tapintf):
        session = ssh(host['host_ip'], host['username'], host['password'])
        self.logger.info('Waiting for tcpdump to complete')
        time.sleep(10)
        output_cmd = 'sudo cat /tmp/%s_out.log' % tapintf
        out, err = execute_cmd_out(session, output_cmd, self.logger)
        return out
    # end stop_tcpdump_on_intf

    def create_service_vms(self, vns, service_mode='transparent', max_inst=1,
            svc_img_name=None, service_type='firewall',
            hosts=[]):
        non_docker_zones = [x for x in self.orch.get_zones() if x != 'nova/docker']
        svm_fixtures = []
        svc_img_name = svc_img_name or SVC_TYPE_PROPS[service_type][service_mode]
        for i in range(max_inst):
            svm_name = get_random_name("pt_svm" + str(i))
            svm_fixture = self.config_vm_only(
                svm_name,
                image_name=svc_img_name,
                vns=vns,
                node_name=hosts[i%len(hosts)] if hosts else None,
                zone=random.choice(non_docker_zones))
            svm_fixtures.append(svm_fixture)
            if service_type == 'analyzer':
                svm_fixture.disable_interface_policy()
        self.verify_vms(svm_fixtures)
        return svm_fixtures
    # end create_service_vms


    def _get_vn_for_config(self,
                          vn_name,
                          vn_subnets,
                          vn_fixture,
                          vn_name_prefix,
                          **kwargs):
        if vn_fixture:
            vn_name = vn_fixture.vn_name
            vn_subnets = [x['cidr'] for x in vn_fixture.vn_subnets]
        else:
            vn_name = vn_name or get_random_name(vn_name_prefix)
            vn_subnets = vn_subnets or \
                                  [get_random_cidr(af=self.inputs.get_af())]
            vn_fixture = vn_fixture or self.config_vn(vn_name, vn_subnets, **kwargs)
        vn_fq_name = vn_fixture.vn_fq_name
        return (vn_name, vn_subnets, vn_fixture, vn_fq_name)
    # end _get_vn_for_config

    def _get_end_vm_image(self, image_name=None):
        if self.inputs.is_ci_setup() and self.inputs.get_af() == 'v4':
            image_name = self.inputs.get_ci_image()
        else:
	    if self.inputs.vcenter_dc:
		image_name = 'ubuntu'
	    else:
	        image_name = image_name or 'ubuntu-traffic'
        return image_name
    # end _get_end_vm_image

    def _get_if_needed(self, svc_img_name, intf_type, value):
        '''
        Returns `value` if intf_type is required to launch svm with
            image svc_img_name. Else returns None

        intf_type : One of management/left/right
        '''
        svm_intf_ctrl = SVC_IMAGE_PROPS.get(svc_img_name)
        if not svm_intf_ctrl:
            return value
        else:
            if svm_intf_ctrl.get(intf_type, True):
                return value
        return None
    # end _get_if_needed


    def config_svc_chain(self,
                        service_mode='transparent',
                        service_type='firewall',
                        max_inst=1,
                        proto='any',
                        src_ports =[0, 65535],
                        dst_ports =[0, 65535],
                        svc_img_name=None,
                        st_version=2,
                        mgmt_vn_name=None,
                        mgmt_vn_subnets=[],
                        mgmt_vn_fixture=None,
                        left_vn_name=None,
                        left_vn_subnets=[],
                        left_vn_fixture=None,
                        right_vn_name=None,
                        right_vn_subnets=[],
                        right_vn_fixture=None,
                        left_vm_name=None,
                        left_vm_fixture=None,
                        right_vm_name=None,
                        right_vm_fixture=None,
                        image_name=None,
                        policy_fixture=None,
                        st_fixture=None,
                        si_fixture=None,
                        port_tuples_props=None,
                        static_route=None,
                        svm_fixtures=[],
                        create_svms=False,
                        hosts=[],
                        **kwargs):
        '''
        service_mode : transparent/in-network/in-network-nat
        '''
        trans_left_vn_name = kwargs.get('trans_left_vn_name', None)
        trans_left_vn_subnets = kwargs.get('trans_left_vn_subnets', [])
        trans_left_vn_fixture = kwargs.get('trans_left_vn_fixture', None)
        trans_right_vn_name = kwargs.get('trans_right_vn_name', None)
        trans_right_vn_subnets = kwargs.get('trans_right_vn_subnets', [])
        trans_right_vn_fixture = kwargs.get('trans_right_vn_fixture', None)

        image_name = self._get_end_vm_image(image_name)

        if self.inputs.vcenter_compute_ips:
            svc_img_name = VC_SVC_TYPE_PROPS[service_type][service_mode]
        elif self.inputs.orchestrator == 'vcenter':#Fixing tinycore image 
                                                   #for vcenter-only mode
            svc_img_name = SVC_TYPE_PROPS[service_type][service_mode]
        else:
            svc_img_name = svc_img_name or SVC_TYPE_PROPS[service_type][service_mode]

        # Mgmt
        (mgmt_vn_name,
         mgmt_vn_subnets,
         mgmt_vn_fixture,
         mgmt_vn_fq_name) = self._get_vn_for_config(mgmt_vn_name,
                                                    mgmt_vn_subnets,
                                                    mgmt_vn_fixture,
                                                    'mgmt_vn',
                                                    **kwargs)

        # Left
        (left_vn_name,
         left_vn_subnets,
         left_vn_fixture,
         left_vn_fq_name) = self._get_vn_for_config(left_vn_name,
                                                    left_vn_subnets,
                                                    left_vn_fixture,
                                                    'left_vn',
                                                    **kwargs)

        # Right
        (right_vn_name,
         right_vn_subnets,
         right_vn_fixture,
         right_vn_fq_name) = self._get_vn_for_config(right_vn_name,
                                                     right_vn_subnets,
                                                     right_vn_fixture,
                                                     'right_vn',
                                                     **kwargs)

        # Transparent SVMs should not be part of left and right VNs
        if service_mode == 'transparent':
            (si_left_vn_name,
             si_left_vn_subnets,
             si_left_vn_fixture,
             si_left_vn_fq_name) = self._get_vn_for_config(trans_left_vn_name,
                                                         trans_left_vn_subnets,
                                                         trans_left_vn_fixture,
                                                         'trans_left_vn',
                                                         **kwargs)
            (si_right_vn_name,
             si_tvn_subnets,
             si_right_vn_fixture,
             si_right_vn_fq_name) = self._get_vn_for_config(trans_right_vn_name,
                                                         trans_right_vn_subnets,
                                                         trans_right_vn_fixture,
                                                         'trans_right_vn',
                                                         **kwargs)
        else :
            si_left_vn_name = left_vn_name
            si_left_vn_subnets = left_vn_subnets
            si_left_vn_fixture = left_vn_fixture
            s_left_vn_fq_name = left_vn_fq_name
            si_right_vn_name = right_vn_name
            si_right_vn_subnets = right_vn_subnets
            si_right_vn_fixture = right_vn_fixture
            si_left_vn_fq_name = si_left_vn_fixture.vn_fq_name
            si_right_vn_fq_name = si_right_vn_fixture.vn_fq_name

        vns = [self._get_if_needed(svc_img_name, 'management', mgmt_vn_fixture),
               self._get_if_needed(svc_img_name, 'left', si_left_vn_fixture),
               self._get_if_needed(svc_img_name, 'right', si_right_vn_fixture)]

        # End VMs
        left_vm_name = left_vm_name or get_random_name('left_vm')
        right_vm_name = right_vm_name or get_random_name('right_vm')
        created_left_vm = False
        created_right_vm = False
        if not left_vm_fixture :
            left_vm_fixture = self.config_vm_only(
                left_vm_name, vn_fix=left_vn_fixture, image_name=image_name)
            created_left_vm = True
        if not right_vm_fixture:
            right_vm_fixture = self.config_vm_only(
                right_vm_name, vn_fix=right_vn_fixture, image_name=image_name)
            created_right_vm = True

        # SI
        if_list = []
        if not st_fixture:
            st_name = kwargs.get('st_name', get_random_name('service_template_1'))
            st_fixture = self.config_st(st_name,
                mgmt=self._get_if_needed(svc_img_name, 'management', mgmt_vn_fq_name),
                left=self._get_if_needed(svc_img_name, 'left', si_left_vn_fq_name),
                right=self._get_if_needed(svc_img_name, 'right', si_right_vn_fq_name),
                st_version=st_version,
                service_mode=service_mode,
                service_type=service_type)
        # Create SI VMs now
        if not svm_fixtures and create_svms:
            svm_fixtures = self.create_service_vms(vns,
                                                   svc_img_name=svc_img_name,
                                                   service_mode=service_mode,
                                                   service_type=service_type,
                                                   hosts=hosts,
                                                   max_inst=max_inst)
        if not si_fixture:
            si_name = get_random_name('si')
            si_fixture = self.config_si(si_name,
                st_fixture,
		 mgmt_vn_fq_name=self._get_if_needed(svc_img_name, 'management', mgmt_vn_fq_name),
                left_vn_fq_name=self._get_if_needed(svc_img_name, 'left', si_left_vn_fq_name),
                right_vn_fq_name=self._get_if_needed(svc_img_name, 'right', si_right_vn_fq_name),
                port_tuples_props=port_tuples_props,
                static_route=static_route,
                max_inst=max_inst,
                svm_fixtures=svm_fixtures)

        if created_left_vm:
            self.verify_vm(left_vm_fixture)
        if created_right_vm:
            self.verify_vm(right_vm_fixture)

        if not policy_fixture:
            policy_name = get_random_name('policy')
            si_fq_name_list = [si_fixture.fq_name_str]

            if service_type == 'analyzer':
                action_list = {'simple_action' : 'pass',
                        'mirror_to': {'analyzer_name': si_fq_name_list[0]}}
            else:
                action_list = {'simple_action' : 'pass',
                        'apply_service': si_fq_name_list}
            rules = [
                {
                    'direction': '<>',
                    'protocol': proto,
                    'source_network': left_vn_fq_name,
                    'src_ports': src_ports,
                    'dest_network': right_vn_fq_name,
                    'dst_ports': dst_ports,
                    'action_list': action_list,
                },
            ]
            policy_fixture = self.config_policy(policy_name, rules)

        # endif policy_fixture
        left_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        right_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)

        ret_dict = {
            'st_fixture' : st_fixture,
            'si_fixture': si_fixture,
            'svm_fixtures' : svm_fixtures,
            'policy_fixture' : policy_fixture,
            'left_vn_policy_fix' : left_vn_policy_fix,
            'right_vn_policy_fix' : right_vn_policy_fix,
            'mgmt_vn_fixture' : mgmt_vn_fixture,
            'left_vn_fixture' : left_vn_fixture,
            'right_vn_fixture' : right_vn_fixture,
            'left_vm_fixture' : left_vm_fixture,
            'right_vm_fixture' : right_vm_fixture,
            'si_left_vn_fixture' : si_left_vn_fixture,
            'si_right_vn_fixture' : si_right_vn_fixture,
        }
        return ret_dict

    def get_svms_in_si(self, si):
        '''
        Returns a list of VMFixture objects
        '''
        (svm_ids, msg) = si.get_vm_refs()
        svm_list= []
        for svm_id in svm_ids:
            svm_list.append(self.orch.get_vm_by_id(svm_id))
        return svm_list
    #end get_svms_in_si

    def add_static_route_in_svm(self, si, vn_fixture, device):
        for subnet in vn_fixture.vn_subnets:
            subnet = subnet['cidr']
            af = ''
            if is_v6(subnet):
                af = '-6'
            for vm in si.svm_list:
                cmd = 'sudo ip %s route add %s dev %s' % (af, subnet, device)
                vm.run_cmd_on_vm([cmd])

    def config_multi_inline_svc(
            self,
            si_list,
            **kwargs):
        '''
        Similar to config_svc_chain , but has multiple SIs as action
        si_list :
            [ {service_mode: 'transparent',
               max_inst : 2,
               st_fixture : <>,
               hosts : [ 'nodek3', 'nodek2'],
               svm_fixtures : <list of svm fixtures>,
               svc_img_name : tiny-in-net }, {},...]
            max_inst     : Default is 1
            svm_fixtures : Default is []
            st_fixture   : Default is None
            svc_img_name : Default is auto ( get from SVC_TYPE_PROPS)
        '''
        svms = []
        create_svms = kwargs.get('create_svms')
        service_type = 'firewall'
        first_si_mode = si_list[0].get('service_mode', 'transparent')
        first_si_max_inst = si_list[0].get('max_inst', 1)
        first_svc_img_name = si_list[0].get('svc_img_name', 'transparent')
        hosts = si_list[0].get('hosts', [])
        ret_dict = self.config_svc_chain(
            service_mode=first_si_mode,
            service_type=service_type,
            max_inst=first_si_max_inst,
            hosts=hosts,
            **kwargs)
        policy_fixture = ret_dict['policy_fixture']
        rules_list = policy_fixture.rules_list
        sis = []
        mgmt_vn_fq_name = getattr(ret_dict.get('mgmt_vn_fixture'),
                                  'vn_fq_name', None)
        left_vn_fq_name = getattr(ret_dict.get('left_vn_fixture'),
                                  'vn_fq_name', None)
        right_vn_fq_name = getattr(ret_dict.get('right_vn_fixture'),
                                  'vn_fq_name', None)
        st_fixtures = [ret_dict['st_fixture']]
        si_fixtures = [ret_dict['si_fixture']]
        svm_fixtures_list = [ret_dict['svm_fixtures']]
        for si in si_list[1:] :
            if si['service_mode'] == 'transparent':
                si_left_vn_fixture = ret_dict.get('si_left_vn_fixture')
                si_right_vn_fixture = ret_dict.get('si_right_vn_fixture')
            else:
                si_left_vn_fixture = ret_dict.get('left_vn_fixture')
                si_right_vn_fixture = ret_dict.get('right_vn_fixture')
            vns = [ ret_dict.get('mgmt_vn_fixture'),
                    si_left_vn_fixture, si_right_vn_fixture ]
            si_name = get_random_name('si')
            st_name = get_random_name('st')
            st_fixture = self.config_st(st_name,
                                        mgmt=mgmt_vn_fq_name,
                                        left=si_left_vn_fixture.vn_fq_name,
                                        right=si_right_vn_fixture.vn_fq_name,
                                        service_mode=si['service_mode'],
                                        service_type=service_type)
            if not si.get('svm_fixtures') and create_svms:
                svms = self.create_service_vms(vns,
                                               service_mode=si.get('service_mode'),
                                               service_type=service_type,
                                               max_inst=si.get('max_inst', 1),
                                               svc_img_name=si.get('svc_img_name'),
                                               hosts=si.get('hosts', []))

            si_fixture = self.config_si(si_name,
                                        st_fixture,
                                        mgmt_vn_fq_name=mgmt_vn_fq_name,
                                        left_vn_fq_name=si_left_vn_fixture.vn_fq_name,
                                        right_vn_fq_name=si_right_vn_fixture.vn_fq_name,
                                        svm_fixtures=svms)
            st_fixtures.append(st_fixture)
            si_fixtures.append(si_fixture)
            svm_fixtures_list.append(svms)
        # end for si

        # Update policy to apply all Sis
        si_fq_names = [x.fq_name_str for x in si_fixtures]
        for rule in rules_list:
            rule['action_list']['apply_service'] = si_fq_names
#            action_list.append(rule)
        policy_fixture.update_policy_api(rules_list)
        ret_dict['policy_fixture'] = policy_fixture
        ret_dict['si_fixtures'] = si_fixtures
        ret_dict['st_fixtures'] = st_fixtures
        ret_dict['svm_fixtures_list'] = svm_fixtures_list

        return ret_dict
    # end config_multi_inline_svc

    def setup_ecmp_config_hash_svc(self, max_inst=1, service_mode='in-network-nat',
                                   ecmp_hash='default',config_level='global'):
        """Validate the ECMP configuration hash with service chaining in network  datapath"""

        # Default ECMP hash with 5 tuple
        if ecmp_hash == 'default':
            ecmp_hash = {"source_ip": True, "destination_ip": True,
                         "source_port": True, "destination_port": True,
                         "ip_protocol": True}

        if ecmp_hash == 'None':
            ecmp_hash_config = {}
            ecmp_hash_config['hashing_configured'] = False
        else:
            ecmp_hash_config = ecmp_hash.copy()
            ecmp_hash_config['hashing_configured'] = True

        # Bringing up base setup. i.e 2 VNs (vn1 and vn2), 2 VMs, 3 service
        # instances, policy for service instance and applying policy on 2 VNs
        ret_dict = self.verify_svc_chain(max_inst=max_inst,
                                         service_mode=service_mode,
                                         create_svms=True,
                                         **self.common_args)
        # ECMP Hash at VMI interface of right_vm (right side)
        right_vm_fixture = ret_dict['right_vm_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        svm_list = [right_vm_fixture]

        if config_level == 'global' or config_level == 'all':
            self.config_ecmp_hash_global(ecmp_hash_config)
        elif config_level == 'vn' or config_level == 'all':
            right_vn_fixture.set_ecmp_hash(ecmp_hash_config)
        elif config_level ==  'vmi' or config_level == 'all':
            self.config_ecmp_hash_vmi(svm_list, ecmp_hash_config)
        return ret_dict
    # end setup_ecmp_config_hash_svc

    def modify_ecmp_config_hash(self, ecmp_hash='default',config_level='global',right_vm_fixture=None,right_vn_fixture=None):
        """Modify the ECMP configuration hash """

        # Default ECMP hash with 5 tuple
        if ecmp_hash == 'default':
            ecmp_hash = {"source_ip": True, "destination_ip": True,
                         "source_port": True, "destination_port": True,
                         "ip_protocol": True}


        if ecmp_hash == 'None':
            ecmp_hash_config = {}
            ecmp_hash_config['hashing_configured'] = False
        else:
            # Explicitly set "False" to individual tuple, incase not set
            ecmp_hash_config = ecmp_hash.copy()
            if not 'source_ip' in ecmp_hash_config:
                ecmp_hash_config['source_ip'] = False
            if not 'destination_ip' in ecmp_hash_config:
                ecmp_hash_config['destination_ip'] = False
            if not 'source_port' in ecmp_hash_config:
                ecmp_hash_config['source_port'] = False
            if not 'destination_port' in ecmp_hash_config:
                ecmp_hash_config['destination_port'] = False
            if not 'ip_protocol' in ecmp_hash_config:
                ecmp_hash_config['ip_protocol'] = False
            ecmp_hash_config['hashing_configured'] = True

        right_vm_fixture = right_vm_fixture or self.right_vm_fixture
        right_vn_fixture = right_vn_fixture or self.right_vn_fixture
        # ECMP Hash at VMI interface of VM2 (right side)
        svm_list = [right_vm_fixture]

        if config_level == 'global' or config_level == 'all':
            self.config_ecmp_hash_global(ecmp_hash_config)
        if config_level == 'vn' or config_level == 'all':
            right_vn_fixture.set_ecmp_hash(ecmp_hash_config)
        if config_level ==  'vmi' or config_level == 'all':
            self.config_ecmp_hash_vmi(svm_list, ecmp_hash_config)
    # end modify_ecmp_config_hash

    def config_ecmp_hash_vmi(self, svm_list, ecmp_hash=None):
        """Configure ecmp hash at vmi"""
        for svm in svm_list:
            for (vn_fq_name, vmi_uuid) in svm.get_vmi_ids().iteritems():
                if re.match(r".*in_network_vn2.*|.*bridge_vn2.*|.*right_.*", vn_fq_name):
                    self.logger.info('Updating ECMP Hash:%s at vmi:%s' % (ecmp_hash, vmi_uuid))
                    vmi_config = self.vnc_lib.virtual_machine_interface_read(id = str(vmi_uuid))
                    vmi_config.set_ecmp_hashing_include_fields(ecmp_hash)
                    self.vnc_lib.virtual_machine_interface_update(vmi_config)
    # end config_ecmp_hash_vmi

    def config_ecmp_hash_global(self, ecmp_hash=None):
        """Configure ecmp hash at global"""
        self.logger.info('Updating ECMP Hash:%s at Global Config Level' % ecmp_hash)
        global_vrouter_id = self.vnc_lib.get_default_global_vrouter_config_id()
        global_config = self.vnc_lib.global_vrouter_config_read(id = global_vrouter_id)
        global_config.set_ecmp_hashing_include_fields(ecmp_hash)
        self.vnc_lib.global_vrouter_config_update(global_config)
    # end config_ecmp_hash_global


    def del_ecmp_hash_config(self, vn_fixture=None, svm_list=None):
        """Delete ecmp hash at global, vn and vmi"""
        self.logger.info('Explicitly deleting ECMP Hash:%s at Global, VN and VMI Level')
        ecmp_hash = {"hashing_configured": False}
        self.config_ecmp_hash_global(ecmp_hash)
        self.config_ecmp_hash_vmi(svm_list, ecmp_hash)
        vn_fixture.set_ecmp_hash(ecmp_hash)
    # end del_ecmp_hash_config

