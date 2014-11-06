import fixtures
import re
from ipam_test import *
from vn_test import *
from tcutils.util import *
import time
import traceback
from fabric.api import env
from fabric.api import run
from fabric.state import output
from fabric.state import connections as fab_connections
from fabric.operations import get, put
from fabric.context_managers import settings, hide
import socket
import paramiko
from contrail_fixtures import *
import threading
import shlex
from subprocess import Popen, PIPE

from tcutils.pkgs.install import PkgHost, build_and_install

env.disable_known_hosts = True
try:
    from webui_test import *
except ImportError:
    pass
#output.debug= True

#@contrail_fix_ext ()


class VMFixture(fixtures.Fixture):

    '''
    Fixture to handle creation, verification and deletion of VM.
    image_name : One of cirros-0.3.0-x86_64-uec, redmine-fe, redmine-be, ubuntu

    Deletion of the VM upon exit can be disabled by setting fixtureCleanup= 'no' in params file.
    If a VM with the vm_name is already present, it is not deleted upon exit. To forcefully clean them up, set fixtureCleanup= 'force'
    Vn object can be a single VN object(vn_obj) or a list of VN objects(vn_objs) but not both
    '''

    def __init__(self, connections, vm_name, vn_obj=None,
                 vn_objs=[], project_name=None,
                 image_name='cirros-0.3.0-x86_64-uec' if os.environ.has_key('ci_image') else 'ubuntu', subnets=[],
                 flavor='contrail_flavor_small',
                 node_name=None, sg_ids=[], count=1, userdata=None,
                 port_ids=[], fixed_ips=[], project_fixture= None):
        self.connections = connections
        self.api_s_inspects = self.connections.api_server_inspects
        self.api_s_inspect = self.connections.api_server_inspect
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.ops_inspect = self.connections.ops_inspects
        self.quantum_fixture = self.connections.quantum_fixture
        self.vnc_lib_fixture = self.connections.vnc_lib_fixture
        self.quantum_h = self.quantum_fixture.get_handle()
        self.vnc_lib_h = self.connections.vnc_lib
        self.nova_fixture = self.connections.nova_fixture
        self.node_name = node_name
        self.sg_ids = sg_ids
        self.count = count
        self.port_ids = port_ids
        self.fixed_ips = fixed_ips

        self.subnets = subnets
#        self.vn_fixture= vn_fixture
        if vn_obj:
            vn_objs = [vn_obj]
            self.vn_obj = vn_obj
        if type(vn_objs) is not list:
            self.vn_objs = [vn_objs]
        else:
            self.vn_objs = vn_objs
        self.flavor = flavor
        self.image_name = image_name
        self.vm_name = vm_name
        self.vm_obj = None
        self.vm_ip = None
        self.agent_vn_obj = {}
        self.vn_names = [x['network']['name'] for x in self.vn_objs]
        # self.vn_fq_names = [':'.join(x['network']['contrail:fq_name'])
        #                    for x in self.vn_objs]
        self.vn_fq_names = [':'.join(self.vnc_lib_h.id_to_fq_name(x['network']['id']))
                            for x in self.vn_objs]
        if len(vn_objs) == 1:
            self.vn_name = self.vn_names[0]
            self.vn_fq_name = self.vn_fq_names[0]
        self.inputs = self.connections.inputs
        self.logger = self.inputs.logger
        if not project_name:
            project_name = self.inputs.stack_tenant
        self.project_name = project_name
        self.already_present = False
        self.verify_is_run = False
        self.analytics_obj = self.connections.analytics_obj
        self.agent_vn_obj = {}
        self.agent_vrf_obj = {}
        self.agent_vrf_name = {}
        self.agent_vrf_id = {}
        self.agent_path = {}
        self.agent_l2_path = {}
        self.tap_intf = {}
        self.mac_addr = {}
        self.agent_label = {}
        self.agent_l2_label = {}
        self.agent_vxlan_id = {}
        self.local_ips = {}
        self.local_ip = None
        self.vm_ip_dict = {}
        self.cs_vmi_obj = {}
        self.vm_launch_flag = True
        self.vm_in_api_flag = True
        self.vm_in_agent_flag = True
        self.vm_in_cn_flag = True
        self.vm_in_op_flag = True
        self.verify_vm_not_in_setup = True
        self.verify_vm_not_in_api_server_flag = True
        self.verify_vm_not_in_agent_flag = True
        self.verify_vm_not_in_control_nodes_flag = True
        self.verify_vm_not_in_nova_flag = True
        self.vm_flows_removed_flag = True
        self.printlock = threading.Lock()
        self.verify_vm_flag = True
        self.userdata = userdata
        self.vm_username = None
        self.vm_password = None
        if self.inputs.verify_thru_gui():
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.webui = WebuiTest(self.connections, self.inputs)
        self.project_fixture = project_fixture
        self.scale = False

    # end __init__

    def setUp(self):
        super(VMFixture, self).setUp()
        if not self.project_fixture:
            self.project_fixture = self.useFixture(
                ProjectFixture(vnc_lib_h=self.vnc_lib_h,
                               project_name=self.project_name,
                               connections=self.connections))
        self.scale = self.project_fixture.scale
        self.vn_ids = [x['network']['id'] for x in self.vn_objs]
        if not self.scale:
            self.vm_obj = self.nova_fixture.get_vm_if_present(
                self.vm_name, self.project_fixture.uuid)
            self.vm_objs = self.nova_fixture.get_vm_list(name_pattern=self.vm_name,
                                                     project_id=self.project_fixture.uuid)
        if self.vm_obj:
            self.already_present = True
            with self.printlock:
                self.logger.debug('VM %s already present, not creating it'
                                  % (self.vm_name))
        else:
            if self.inputs.is_gui_based_config():
                self.webui.create_vm(self)
            else:
                objs = self.nova_fixture.create_vm(
                    project_uuid=self.project_fixture.uuid,
                    image_name=self.image_name,
                    flavor=self.flavor,
                    vm_name=self.vm_name,
                    vn_ids=self.vn_ids,
                    node_name=self.node_name,
                    sg_ids=self.sg_ids,
                    count=self.count,
                    userdata=self.userdata,
                    port_ids=self.port_ids,
                    fixed_ips=self.fixed_ips)
                time.sleep(5)
                self.vm_obj = objs[0]
                self.vm_objs = objs
        (self.vm_username, self.vm_password) = self.nova_fixture.get_image_account(
            self.image_name)

    # end setUp

    def verify_vm_launched(self):
        self.vm_ips = []
        self.vm_launch_flag = True
        self.vm_id = self.vm_objs[0].id
        for vm_obj in self.vm_objs:
            vm_id = vm_obj.id
            self.nova_fixture.get_vm_detail(vm_obj)

            for vn_name in self.vn_names:
                if len(self.nova_fixture.get_vm_ip(vm_obj, vn_name)) == 0:
                    with self.printlock:
                        self.logger.error('VM %s did not seem to have got any IP'
                                          % (vm_obj.name))
                    self.vm_launch_flag = self.vm_launch_flag and False
                    return False
                for ip in self.nova_fixture.get_vm_ip(vm_obj, vn_name):
                    self.vm_ips.append(ip)
            with self.printlock:
                self.logger.info('VM %s launched on Node %s'
                                 % (vm_obj.name, self.nova_fixture.get_nova_host_of_vm(vm_obj)))
            if len(self.vm_ips) >= 1:
                self.vm_ip = self.nova_fixture.get_vm_ip(
                    self.vm_obj, self.vn_names[0])[0]
            else:
                with self.printlock:
                    self.logger.error('VM %s did not seem to have got an IP '
                                      'at all ' % (vm_obj.name))
                self.vm_launch_flag = self.vm_launch_flag and False
                return False
            with self.printlock:
                self.logger.info("VM %s ID is %s" % (vm_obj.name, vm_obj.id))
        # end for  vm_obj
        self.vm_launch_flag = self.vm_launch_flag and True
        return True
    # end verify_vm_launched

    def add_security_group(self, secgrp):
        self.nova_fixture.add_security_group(self.vm_obj.id, secgrp)

    def remove_security_group(self, secgrp):
        self.nova_fixture.remove_security_group(self.vm_obj.id, secgrp)

    def verify_security_group(self, secgrp):
        cs_vmi_objs = self.api_s_inspect.get_cs_vmi_of_vm(
            self.vm_id, refresh=True)
        for cs_vmi_obj in cs_vmi_objs:
            vmi = cs_vmi_obj['virtual-machine-interface']
            if vmi.has_key('security_group_refs'):
                sec_grps = vmi['security_group_refs']
                for sec_grp in sec_grps:
                    if secgrp == sec_grp['to'][-1]:
                        self.logger.info(
                            "Security group %s is attached \                                           to the VM %s", secgrp, self.vm_name)
                        return True, None

        errmsg = "Security group %s is not attached to the VM %s" % (secgrp,
                                                                     self.vm_name)
        self.logger.warn(errmsg)
        return False, errmsg

    def verify_on_setup(self, force=False):
        if not (self.inputs.verify_on_setup or force):
            self.logger.info('Skipping VM %s verification' % (self.vm_name))
            return True
        result = True
        self.verify_vm_launched()
        if not self.vm_ip:
            result = result and False
            return result
        vm_status = self.nova_fixture.wait_till_vm_is_active(self.vm_obj)
        if vm_status[1] in 'ERROR':
            self.logger.warn("VM in error state. Asserting...")
            return False

        if vm_status[1] != 'ACTIVE':
            result = result and False
            return result

        self.verify_vm_flag = result and vm_status[0] 
        if self.inputs.verify_thru_gui():
            self.webui.verify_vm(self)
        result = result and self.verify_vm_in_api_server()
        if not result:
            self.logger.error('VM %s verification in API Server failed'
                                  % (self.vm_name))
            return result
        result = result and self.verify_vm_in_agent()
        if not result:
            self.logger.error('VM %s verification in Agent failed'
                                  % (self.vm_name))
            return result
        result = result and self.verify_vm_in_control_nodes()
        if not result:
            self.logger.error('Route verification for VM %s in Controlnodes'
                                  ' failed ' % (self.vm_name))
            return result
        result = result and self.verify_vm_in_opserver()
        if not result:
            self.logger.error('VM %s verification in Opserver failed'
                              % (self.vm_name))
            return result

        self.verify_is_run = True
        return result
    # end verify_on_setup

    def mini_verify_on_setup(self):
        result = True
        if not self.verify_vm_launched():
            return False
        if not self.verify_vm_in_api_server():
            self.logger.error('VM %s verification in API Server failed'
                              % (self.vm_name))
            result = result and False
        if not self.verify_vm_in_agent():
            self.logger.error('VM %s verification in Agent failed'
                              % (self.vm_name))
            result = result and False
        self.verify_is_run = True
        return result
    # end mini_verify_on_setup

    def get_vrf_id(self, vn_fq_name, vn_vrf_name):
        inspect_h = self.agent_inspect[self.vm_node_ip]
        (domain, project, vn) = vn_fq_name.split(':')
        agent_vrf_objs_vn = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj_vn = self.get_matching_vrf(
            agent_vrf_objs_vn['vrf_list'],
            vn_vrf_name)
        vn_vrf_id = agent_vrf_obj_vn['ucindex']
        return vn_vrf_id

    # end get_vrf_id

    def chk_vmi_for_vrf_entry(self, vn_fq_name):
        try:
            cs_vmi_obj = {}
            cs_vmi_objs_vm = self.api_s_inspect.get_cs_vmi_of_vm(self.vm_id)
            inspect_h = self.agent_inspect[self.vm_node_ip]
            for vmi_obj in cs_vmi_objs_vm:
                vmi_id = vmi_obj[
                    'virtual-machine-interface']['virtual_network_refs'][0]['uuid']
                vmi_vn_fq_name = ':'.join(
                    vmi_obj['virtual-machine-interface']['virtual_network_refs'][0]['to'])
                cs_vmi_obj[vmi_vn_fq_name] = vmi_obj
                tap_intf = {}
                tmp_vmi_id = cs_vmi_obj[vmi_vn_fq_name][
                    'virtual-machine-interface']['uuid']
                tap_intf[vn_fq_name] = inspect_h.get_vna_tap_interface_by_vmi(
                    vmi_id=tmp_vmi_id)[0]
                vrf_entry = tap_intf[vn_fq_name]['fip_list'][0]['vrf_name']
            return vrf_entry
        except IndexError, e:
            self.logger.error('No VRF Entry listed')
            return None

        # end chk_vmi_for_vrf_entry

    def chk_vmi_for_fip(self, vn_fq_name):
        try:
            cs_vmi_obj = {}
            cs_vmi_objs_vm = self.api_s_inspect.get_cs_vmi_of_vm(self.vm_id)
            inspect_h = self.agent_inspect[self.vm_node_ip]
            for vmi_obj in cs_vmi_objs_vm:
                vmi_id = vmi_obj[
                    'virtual-machine-interface']['virtual_network_refs'][0]['uuid']
                vmi_vn_fq_name = ':'.join(
                    vmi_obj['virtual-machine-interface']['virtual_network_refs'][0]['to'])
                cs_vmi_obj[vmi_vn_fq_name] = vmi_obj
                tap_intf = {}
                tmp_vmi_id = vmi_id = cs_vmi_obj[vmi_vn_fq_name][
                    'virtual-machine-interface']['uuid']
                tap_intf = inspect_h.get_vna_tap_interface_by_vmi(
                    vmi_id=tmp_vmi_id)[0]
                fip_list = tap_intf['fip_list']
                for fip in fip_list:
                    if vn_fq_name in fip['vrf_name']:
                        fip_addr_vm = fip['ip_addr']
                        return fip_addr_vm
        except IndexError, e:
            self.logger.error('No FIP Address listed')
            return None
        # end chk_vmi_for_fip

    @retry(delay=2, tries=15)
    def verify_vm_in_api_server(self):
        '''Validate API-Server objects for a VM.

        Checks if Instance IP in API Server is same as what
        Orchestration system gave it.
        Checks if the virtual-machine-interface's VN in API Server is correct.
        '''
        self.vm_in_api_flag = True
        self.cs_vm_obj = {}
        self.cs_vmi_objs = {}
        self.cs_instance_ip_objs = {}

        # for ha testing modify the curr cfgm ips
        if self.inputs.cfgm_ips_curr:
            cfgm_ips = self.inputs.cfgm_ips_curr
        else:
            cfgm_ips = self.inputs.cfgm_ips

        for cfgm_ip in cfgm_ips:
            api_inspect = self.api_s_inspects[cfgm_ip]
            self.cs_vm_obj[cfgm_ip] = api_inspect.get_cs_vm(self.vm_id)
            self.cs_vmi_objs[
                cfgm_ip] = api_inspect.get_cs_vmi_of_vm(self.vm_id)
            self.cs_instance_ip_objs[
                cfgm_ip] = api_inspect.get_cs_instance_ips_of_vm(self.vm_id)

        for cfgm_ip in cfgm_ips:
            self.logger.info("Verifying in api server %s" % (cfgm_ip))
            if not self.cs_instance_ip_objs[cfgm_ip]:
                with self.printlock:
                    self.logger.error('Instance IP of VM ID %s not seen in '
                                      'API Server ' % (self.vm_id))
                self.vm_in_api_flag = self.vm_in_api_flag and False
                return False

            for instance_ip_obj in self.cs_instance_ip_objs[cfgm_ip]:
                ip = instance_ip_obj['instance-ip']['instance_ip_address']
                if ip not in self.vm_ips:
                    with self.printlock:
                        self.logger.warn('Instance IP %s from API Server is '
                                         ' not found in VM IP list %s' % (ip, str(self.vm_ips)))
                    self.vm_in_api_flag = self.vm_in_api_flag and False
                    return False
                ip_vn_fq_name = ':'.join(
                    instance_ip_obj['instance-ip']['virtual_network_refs'][0]['to'])
                self.vm_ip_dict[ip_vn_fq_name] = ip
            for vmi_obj in self.cs_vmi_objs[cfgm_ip]:
                vmi_id = vmi_obj[
                    'virtual-machine-interface']['virtual_network_refs'][0]['uuid']
                vmi_vn_fq_name = ':'.join(
                    vmi_obj['virtual-machine-interface']['virtual_network_refs'][0]['to'])
                if vmi_id not in self.vn_ids:
                    with self.printlock:
                        self.logger.warn('VMI %s of VM %s is not mapped to the '
                                         'right VN ID in API Server' % (vmi_id, self.vm_name))
                    self.vm_in_api_flag = self.vm_in_api_flag and False
                    return False
                self.cs_vmi_obj[vmi_vn_fq_name] = vmi_obj
            with self.printlock:
                self.logger.info("API Server validations for VM %s passed in api server %s"
                                 % (self.vm_name, cfgm_ip))
        with self.printlock:
            self.logger.info("API Server validations for VM %s passed"
                             % (self.vm_name))
        self.vm_in_api_flag = self.vm_in_api_flag and True
        return True
    # end verify_vm_in_api_server

    @retry(delay=2, tries=15)
    def verify_vm_not_in_api_server(self):

        if self.inputs.cfgm_ips_curr:
            cfgm_ips = self.inputs.cfgm_ips_curr
        else:
            cfgm_ips = self.inputs.cfgm_ips

        self.verify_vm_not_in_api_server_flag = True
        for ip in cfgm_ips:
            self.logger.info("Verifying in api server %s" % (ip))
            api_inspect = self.api_s_inspects[ip]
            if api_inspect.get_cs_vm(self.vm_id, refresh=True) is not None:
                with self.printlock:
                    self.logger.warn("VM ID %s of VM %s is still found in API Server"
                                     % (self.vm_id, self.vm_name))
                self.verify_vm_not_in_api_server_flag = self.verify_vm_not_in_api_server_flag and False
                return False
            if api_inspect.get_cs_vr_of_vm(self.vm_id, refresh=True) is not None:
                with self.printlock:
                    self.logger.warn('API-Server still seems to have VM reference '
                                     'for VM %s' % (self.vm_name))
                self.verify_vm_not_in_api_server_flag = self.verify_vm_not_in_api_server_flag and False
                return False
            if api_inspect.get_cs_vmi_of_vm(
                    self.vm_id, refresh=True) is not None:
                with self.printlock:
                    self.logger.warn("API-Server still has VMI info of VM %s"
                                     % (self.vm_name))
                self.verify_vm_not_in_api_server_flag = self.verify_vm_not_in_api_server_flag and False
                return False
            with self.printlock:
                self.logger.info(
                    "VM %s information is fully removed in API-Server " % (self.vm_name))
            self.verify_vm_not_in_api_server_flag = self.verify_vm_not_in_api_server_flag and True
        return True
    # end verify_vm_not_in_api_server

    @retry(delay=2, tries=20)
    def verify_vm_in_agent(self):
        ''' Verifies whether VM has got created properly in agent.

        '''
        self.vm_in_agent_flag = True
        nova_host = self.inputs.host_data[
            self.nova_fixture.get_nova_host_of_vm(self.vm_obj)]
        self.vm_node_ip = nova_host['host_ip']
        self.vm_node_data_ip = nova_host['host_data_ip']
        inspect_h = self.agent_inspect[self.vm_node_ip]

        for vn_fq_name in self.vn_fq_names:

            fw_mode = self.vnc_lib_fixture.get_forwarding_mode(vn_fq_name)
            (domain, project, vn) = vn_fq_name.split(':')
            self.agent_vn_obj[vn_fq_name] = inspect_h.get_vna_vn(
                domain, project, vn)
            if not self.agent_vn_obj[vn_fq_name]:
                self.logger.warn('VN %s is not seen in agent %s'
                                 % (vn_fq_name, self.vm_node_ip))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False

            # Check if the VN ID matches between the Orchestration S and Agent
#            if self.vn_id != self.agent_vn_obj['uuid']:
            if self.agent_vn_obj[vn_fq_name]['uuid'] not in self.vn_ids:
                self.logger.warn('Unexpected VN UUID %s found in agent %s '
                    'Expected: One of %s' % (
                    self.agent_vn_obj[vn_fq_name]['uuid'], 
                    self.vm_node_ip,
                    self.vn_ids))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False
            try:
                vna_tap_id = inspect_h.get_vna_tap_interface_by_vmi(
                    vmi_id=self.cs_vmi_obj[vn_fq_name]['virtual-machine-interface']['uuid'])
            except Exception as e:
                return False
            if not vna_tap_id:
                self.logger.warn("tap id not returned")
                return False

            self.tap_intf[vn_fq_name] = vna_tap_id[0]
            if not self.tap_intf[vn_fq_name]:
                self.logger.error('Tap interface in VN %s for VM %s not' 
                                      'seen in agent %s '
                                      % (vn_fq_name, self.vm_name, self.vm_node_ip))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False
            self.mac_addr[vn_fq_name] = self.tap_intf[vn_fq_name]['mac_addr']
            if self.mac_addr[vn_fq_name] != self.cs_vmi_obj[vn_fq_name]['virtual-machine-interface']['virtual_machine_interface_mac_addresses']['mac_address'][0]:
                with self.printlock:
                    self.logger.error('VM Mac address for VM %s not seen in' 
                                      'agent %s or VMI mac is not matching with API' 
                                      'Server information' % (self.vm_name, self.vm_node_ip))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False
            try:
                self.tap_intf[vn_fq_name] = inspect_h.get_vna_intf_details(
                    self.tap_intf[vn_fq_name]['name'])[0]
            except Exception as e:
                return False

            self.logger.info("tap intf: %s"%(str(self.tap_intf[vn_fq_name])))

            self.agent_vrf_name[vn_fq_name] = self.tap_intf[
                vn_fq_name]['vrf_name']

            self.logger.info("agent vrf name: %s"%(str(self.agent_vrf_name[vn_fq_name])))

            try:
                self.agent_vrf_objs = inspect_h.get_vna_vrf_objs(
                    domain, project, vn)
            except Exception as e:
                return False

            self.logger.info("vrf obj : %s"%(str(self.agent_vrf_objs)))
            if not self.agent_vrf_objs:
                self.logger.info("vrf obj : %s"%(str(self.agent_vrf_objs)))
                return False
            #Bug 1372858 
            try:
                self.agent_vrf_obj[vn_fq_name] = self.get_matching_vrf(
                    self.agent_vrf_objs['vrf_list'],
                    self.agent_vrf_name[vn_fq_name])
            except Exception as e:
                self.logger.warn("Exception: %s"%(e))
                return False 
    
            self.agent_vrf_id[vn_fq_name] = self.agent_vrf_obj[
                vn_fq_name]['ucindex']
            if fw_mode != unicode('l2'):
                try:
                   vm_ip=self.vm_ip_dict[vn_fq_name]
                   if ':' in vm_ip :
                       self.agent_path[vn_fq_name] = inspect_h.get_ipv6_vna_active_route(
                                                     vrf_id=self.agent_vrf_id[vn_fq_name],
                                                     ip=self.vm_ip_dict[vn_fq_name],
                                                      prefix='128')
                   else:
                       self.agent_path[vn_fq_name] = inspect_h.get_vna_active_route(
                                                     vrf_id=self.agent_vrf_id[vn_fq_name],
                                                     ip=self.vm_ip_dict[vn_fq_name],
                                                      prefix='32')
                except Exception as e:
                    return False
                if not self.agent_path:
                    with self.printlock:
                        self.logger.warning('No path seen for VM IP %s in agent %s'
                                            % (self.vm_ip_dict[vn_fq_name], self.vm_node_ip))
                    self.vm_in_agent_flag = self.vm_in_agent_flag and False
                    return False
                self.agent_label[vn_fq_name] = self.agent_path[
                    vn_fq_name]['path_list'][0]['label']

                # Check if Tap interface of VM is present in the Agent route
                # table
                if self.agent_path[vn_fq_name]['path_list'][0]['nh']['itf'] != self.tap_intf[vn_fq_name]['name']:
                    self.logger.warning("Active route in agent for %s is not" 
                                       " pointing to right tap interface. It is %s "
                                        % (self.vm_ip_dict[vn_fq_name],
                                           self.agent_path[vn_fq_name]['path_list'][0]['nh']['itf']))
                    self.vm_in_agent_flag = self.vm_in_agent_flag and False
                    return False
                else:
                    self.logger.debug('Active route in agent is present for VMI '
                                          '%s ' % (self.tap_intf[vn_fq_name]['name']))

                if self.tap_intf[vn_fq_name]['label'] != self.agent_label[vn_fq_name]:
                    self.logger.warning('VM %s label mismatch! , Expected : %s ,'
                                            ' Got : %s' % (self.vm_name,
                                                           self.tap_intf[
                                                               vn_fq_name][
                                                               'label'],
                                                           self.agent_label[vn_fq_name]))
                    self.vm_in_agent_flag = self.vm_in_agent_flag and False
                    return False
                else:
                    self.logger.debug('VM %s labels in tap-interface and the '
                                          'route do match ' % (self.vm_name))

                # Check if tap interface is set to Active
                if self.tap_intf[vn_fq_name]['active'] != 'Active':
                    self.logger.warn('VM %s : Tap interface %s is not set to '
                                         'Active, it is : %s ' % (self.vm_name,
                                                                  self.tap_intf[
                                                                      vn_fq_name][
                                                                      'name'],
                                                                  self.tap_intf[vn_fq_name]['active']))
                else:
                    self.logger.debug('VM %s : Tap interface %s is set to '
                                          ' Active' % (self.vm_name,
                                                       self.tap_intf[vn_fq_name]['name']))
                self.local_ips[vn_fq_name] = self.tap_intf[
                    vn_fq_name]['mdata_ip_addr']
                with self.printlock:
                    self.logger.debug('VM %s : Tap interface %s is set to '
                                      ' Active' % (self.vm_name,
                                                   self.tap_intf[vn_fq_name]['name']))
            self.local_ips[vn_fq_name] = self.tap_intf[
                vn_fq_name]['mdata_ip_addr']
            with self.printlock:
                self.logger.debug('Tap interface %s detail : %s' % (
                    self.tap_intf[vn_fq_name]['name'], self.tap_intf[vn_fq_name]))

            with self.printlock:
                self.logger.info('Starting Layer 2 verification in Agent')
            # L2 verification
            try:
                self.agent_l2_path[vn_fq_name] = inspect_h.get_vna_layer2_route(
                    vrf_id=self.agent_vrf_id[vn_fq_name],
                mac=self.mac_addr[vn_fq_name])
            except Exception as e:
                return False    
            if not self.agent_l2_path[vn_fq_name]:
                with self.printlock:
                    self.logger.warning('No Layer 2 path is seen for VM MAC '
                                        '%s in agent %s' % (self.mac_addr[vn_fq_name],
                                                            self.vm_node_ip))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False
            else:
                with self.printlock:
                    self.logger.info('Layer 2 path is seen for VM MAC %s '
                                     'in agent %s' % (self.mac_addr[vn_fq_name],
                                                      self.vm_node_ip))
            self.agent_l2_label[vn_fq_name] = self.agent_l2_path[
                vn_fq_name]['routes'][0]['path_list'][0]['label']
            self.agent_vxlan_id[vn_fq_name] = self.agent_l2_path[
                vn_fq_name]['routes'][0]['path_list'][0]['vxlan_id']

            # Check if Tap interface of VM is present in the Agent layer
            # route table
            if self.agent_l2_path[vn_fq_name]['routes'][0]['path_list'][0]['nh']['itf'] != self.tap_intf[vn_fq_name]['name']:
                with self.printlock:
                    self.logger.warning("Active layer 2 route in agent for "
                                        "%s is not pointing to right tap interface. It is %s "
                                        '' % (self.vm_ip_dict[vn_fq_name],
                                              self.agent_l2_path[vn_fq_name]['routes'][0]['path_list'][0]['nh']['itf']))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False
            else:
                with self.printlock:
                    self.logger.info(
                        'Active layer 2 route in agent is present for VMI %s ' %
                        (self.tap_intf[vn_fq_name]['name']))

            # TODO layer 2 label match is not possibole now as intreface introspect does not have l2 label now.
            # Bug 1730
            # L2 verification end here
            # Check if VN for the VM and route for the VM is present on all
            # compute nodes
            if not self.verify_in_all_agents(vn_fq_name):
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False

        # end for vn_fq_name in self.vn_fq_names
        self.local_ip = self.local_ips.values()[0]

        # Ping to VM IP from host
        ping_result = False
        for vn_fq_name in self.vn_fq_names:
            if self.local_ips[vn_fq_name] != '0.0.0.0':
                if self.ping_vm_from_host(vn_fq_name) or self.ping_vm_from_host(vn_fq_name):
                    ping_result = True
                    self.local_ip = self.local_ips[vn_fq_name]
                    with self.printlock:
                        self.logger.info('The local IP is %s' % self.local_ip)
                    break
        if not ping_result:
            with self.printlock:
                self.logger.error('Ping to one of the 169.254.x.x IPs of the VM '
                                  'should have passed. It failed! ')
            self.vm_in_agent_flag = self.vm_in_agent_flag and False
            return False
        with self.printlock:
            self.logger.info("VM %s Verifications in Agent is fine" %
                             (self.vm_name))
        self.vm_in_agent_flag = self.vm_in_agent_flag and True
        return True
    # end verify_vm_in_agent

    def get_matching_vrf(self, vrf_objs, vrf_name):
        self.logger.info("vrf_objs: %s"%(str(vrf_objs)))
        self.logger.info("vrf_name: %s"%(str(vrf_name)))
        return [x for x in vrf_objs if x['name'] == vrf_name][0]

    def reset_state(self, state):
        self.obj.reset_state(state)

    def ping_vm_from_host(self, vn_fq_name):
        ''' Ping the VM metadata IP from the host
        '''
        if self.scale:
            return True
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (host['username'], self.vm_node_ip),
                password=host['password'],
                    warn_only=True, abort_on_prompts=False):
                output = run('ping %s -c 1' % (self.local_ips[vn_fq_name]))
                expected_result = ' 0% packet loss'
                self.logger.debug(output)
                if expected_result not in output:
                    self.logger.warn(
                        "Ping to Metadata IP %s of VM %s failed!" %
                        (self.local_ips[vn_fq_name], self.vm_name))
                    return False
                else:
                    self.logger.info(
                        'Ping to Metadata IP %s of VM %s passed' %
                        (self.local_ips[vn_fq_name], self.vm_name))
        return True
    # end ping_vm_from_host

    def verify_in_all_agents(self, vn_fq_name):
        ''' Verify if the corresponding VN for a VM is present in all compute nodes.
            Also verifies that a route is present in all compute nodes for the VM IP
        '''
        # for ha testing checking the curr nodes to verify
        if self.inputs.compute_ips_curr:
            compute_ips = self.inputs.compute_ips_curr
        else:
            compute_ips = self.inputs.compute_ips

        (domain, project, vn_name) = vn_fq_name.split(':')
        for compute_ip in compute_ips:
            inspect_h = self.agent_inspect[compute_ip]
            vn = inspect_h.get_vna_vn(domain, project, vn_name)
# The VN for the VM under test may or may not be present on other agent
# nodes. Proceed to check only if VN is present
            if vn is None:
                continue

            if vn['name'] != vn_fq_name:
                self.logger.warn(
                    'VN %s in agent is not the same as expected : %s ' %
                    (vn['name'], vn_fq_name))
                return False
            else:
                self.logger.debug('VN %s is found in Agent of node %s' %
                                  (vn['name'], compute_ip))
            if not vn['uuid'] in self.vn_ids:
                self.logger.warn(
                    'VN ID %s from agent is in VN IDs list %s of the VM in '
                    'Agent node %s' % (vn['uuid'], self.vn_ids, compute_ip))
                return False
# TODO : To be uncommented once the sandesh query with service-chaining works
#            if vn['vrf_name'] != self.agent_vrf_name :
#                self.logger.warn('VN VRF of %s in agent is not the same as expected VRF of %s' %( vn['vrf_name'], self.agent_vrf_name ))
#                return False
            agent_vrf_objs = inspect_h.get_vna_vrf_objs(
                domain, project, vn_name)
            agent_vrf_obj = self.get_matching_vrf(
                self.agent_vrf_objs['vrf_list'],
                self.agent_vrf_name[vn_fq_name])
            agent_vrf_id = self.agent_vrf_obj[vn_fq_name]['ucindex']
            if agent_vrf_id != self.agent_vrf_id[vn_fq_name]:
                self.logger.warn(
                    'VRF id of VN %s is not the same across all agents. '
                    'Expected : %s, Seen : %s' % (vn['name'],
                                                  self.agent_vrf_id[vn_fq_name], agent_vrf_id))
                return False
            fw_mode = self.vnc_lib_fixture.get_forwarding_mode(vn_fq_name)
            if fw_mode != unicode('l2'):
                agent_path = inspect_h.get_vna_active_route(
                    vrf_id=self.agent_vrf_id[vn_fq_name],
                    ip=self.vm_ip_dict[vn_fq_name], prefix='32')
                agent_label = self.agent_path[
                    vn_fq_name]['path_list'][0]['label']
                if agent_label != self.agent_label[vn_fq_name]:
                    self.logger.warn(
                        'The route for VM IP %s in Node %s is having incorrect '
                        'label. Expected : %s, Seen : %s' % (
                            self.vm_ip_dict[vn_fq_name], compute_ip,
                            self.agent_label[vn_fq_name], agent_label))
                    return False

                self.logger.debug(
                    'VRF IDs of VN %s is consistent in agent %s' %
                    (vn_fq_name, compute_ip))
                self.logger.debug(
                    'Route for VM IP %s is consistent in agent %s ' %
                    (self.vm_ip_dict[vn_fq_name], compute_ip))
                self.logger.debug(
                    'VN %s verification for VM %s  in Agent %s passed ' %
                    (vn_fq_name, self.vm_name, compute_ip))

            self.logger.info(
                'Starting all layer 2 verification in agent %s' % (compute_ip))
            agent_l2_path = inspect_h.get_vna_layer2_route(
                vrf_id=self.agent_vrf_id[vn_fq_name],
                mac=self.mac_addr[vn_fq_name])
            agent_l2_label = self.agent_l2_path[vn_fq_name][
                'routes'][0]['path_list'][0]['label']
            if agent_l2_label != self.agent_l2_label[vn_fq_name]:
                self.logger.warn('The route for VM MAC %s in Node %s '
                                 'is having incorrect label. Expected : %s, Seen : %s'
                                 % (self.mac_addr[vn_fq_name], compute_ip,
                                    self.agent_l2_label[vn_fq_name], agent_l2_label))
                return False
            self.logger.info(
                'Route for VM MAC %s is consistent in agent %s ' %
                (self.mac_addr[vn_fq_name], compute_ip))
        # end for
        return True
    # end verify_in_all_agents

    def ping_to_ip(self, ip, return_output=False, other_opt='', size='56', count='5'):
        '''Ping from a VM to an IP specified.

        This method logs into the VM from the host machine using ssh and runs ping test to an IP.
        '''
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        fab_connections.clear()
        try:
            self.nova_fixture.put_key_file_to_host(self.vm_node_ip)
            with hide('everything'):
                with settings(host_string='%s@%s' % (host['username'],
                                                     self.vm_node_ip), password=host[
                    'password'],
                        warn_only=True, abort_on_prompts=False):
                    key_file = self.nova_fixture.tmp_key_file
                    output = run_fab_cmd_on_node(
                        host_string='%s@%s' % (
                            self.vm_username, self.local_ip),
                        password=self.vm_password,
                        cmd='ping -s %s -c %s %s %s' % (str(size), str(count), other_opt, ip))
                    self.logger.debug(output)
            if return_output == True:
                # return_list=[]
                return output
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying ping from VM ')
            return False
        expected_result = ' 0% packet loss'
        try:
            if expected_result not in output:
                self.logger.warn("Ping to IP %s from VM %s failed" %
                             (ip, self.vm_name))
                return False
            else:
                self.logger.info('Ping to IP %s from VM %s passed' %
                             (ip, self.vm_name))
            return True

        except Exception as e:
            self.logger.warn("Got exception in ping_to_ip")
            return False
    # end ping_to_ip

    def ping_to_ipv6(self, ipv6, return_output=False, other_opt='', count='5', intf='eth0'):
        '''Ping from a VM to an IPV6 specified.

        This method logs into the VM from the host machine using ssh and runs ping6 test to an IPV6.
        '''
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        fab_connections.clear()
        try:
            self.nova_fixture.put_key_file_to_host(self.vm_node_ip)
            with hide('everything'):
                with settings(
                    host_string='%s@%s' % (
                        host['username'], self.vm_node_ip),
                    password=host['password'],
                        warn_only=True, abort_on_prompts=False):
                    key_file = self.nova_fixture.tmp_key_file
                    output = run_fab_cmd_on_node(
                        host_string='%s@%s' % (
                            self.vm_username, self.local_ip),
                        password=self.vm_password,
                        cmd='ping6 -I %s -c %s %s %s' % (str(intf), str(count), other_opt, ipv6))
                    self.logger.debug(output)
            if return_output == True:
                return output
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying ping from VM ')
            return False
        expected_result = ' 0% packet loss'
        if expected_result not in output:
            self.logger.warn("Ping6 to IPv6 %s from VM %s failed" %
                             (ipv6, self.vm_name))
            return False
        else:
            self.logger.debug('Ping6 to IP %s from VM %s passed' %
                              (ipv6, self.vm_name))
        return True
    # end ping_to_ipv6

    @retry(delay=1, tries=20)
    def ping_with_certainty(self, ip, return_output=False, other_opt='', size='56', count='5', expectation=True):
        '''
        Better to call this instead of ping_to_ip.
        Set expectation to False if you want ping to fail
        Can be used for both ping pass and fail scenarios with retry
        '''
        if expectation:
            return self.ping_to_ip(ip, return_output, other_opt, size, count)
        else:
            return not self.ping_to_ip(ip, return_output, other_opt, size, count)

    @retry(delay=2, tries=20)
    def verify_vm_not_in_agent(self):
        '''Verify that the VM is fully removed in all Agents.

        '''
        result = True
        self.verify_vm_not_in_agent_flag = True
        inspect_h = self.agent_inspect[self.vm_node_ip]
        if self.vm_obj in self.nova_fixture.get_vm_list():
            with self.printlock:
                self.logger.warn("VM %s is still found in Compute(nova) "
                                 "server-list" % (self.vm_name))
            self.verify_vm_not_in_agent_flag = self.verify_vm_not_in_agent_flag and False
            result = result and False
        # Check if VM is in agent's active VMList:
        if self.vm_id in inspect_h.get_vna_vm_list():
            with self.printlock:
                self.logger.warn("VM %s is still present in agent's active "
                                 "VMList" % (self.vm_name))
            self.verify_vm_not_in_agent_flag = self.verify_vm_not_in_agent_flag and False
            result = result and False
        if len(inspect_h.get_vna_tap_interface_by_vm(vm_id=self.vm_id)) != 0:
            with self.printlock:
                self.logger.warn("VMI/TAP interface(s) is still seen for VM "
                                 "%s in agent" % (self.vm_name))
            self.verify_vm_not_in_agent_flag = self.verify_vm_not_in_agent_flag and False
            result = result and False
        for k,v in self.vrfs.items():
            inspect_h = self.agent_inspect[k]
            for vn_fq_name in self.vn_fq_names:
                if inspect_h.get_vna_active_route(
                                     vrf_id=v[vn_fq_name], 
                                     ip=self.vm_ip_dict[vn_fq_name],
                                     prefix='32') is not None:
                    self.logger.warn(
                        "Route for VM %s, IP %s is still seen in agent %s " %
                        (self.vm_name, self.vm_ip_dict[vn_fq_name], ip))
                    self.verify_vm_not_in_agent_flag = self.verify_vm_not_in_agent_flag and False
                    result = result and False
        #for vn_fq_name in self.vn_fq_names:
        #    for compute_ip in self.inputs.compute_ips:
        #        inspect_h = self.agent_inspect[compute_ip]
        #        if inspect_h.get_vna_active_route(
        #                vrf_id=self.vrfs[compute_ip][vn_fq_name],
        #                ip=self.vm_ip_dict[vn_fq_name],
        #                prefix='32') is not None:
        #            self.logger.warn(
        #                "Route for VM %s, IP %s is still seen in agent %s " %
        #                (self.vm_name, self.vm_ip_dict[vn_fq_name], compute_ip))
        #            self.verify_vm_not_in_agent_flag = self.verify_vm_not_in_agent_flag and False
        #            result = result and False
            if result:
                self.logger.info(
                    "VM %s is removed in Compute, and routes are removed "
                    "in all agent nodes" % (self.vm_name))
        return result
    # end verify_vm_not_in_agent

    @retry(delay=2, tries=20)
    def verify_vm_routes_not_in_agent(self):
        '''Verify that the VM routes is fully removed in all Agents. This will specfically address the scenario where VM interface is down ir shutoff
        '''
        result = True
        inspect_h = self.agent_inspect[self.vm_node_ip]
        for vn_fq_name in self.vn_fq_names:
            for compute_ip in self.inputs.compute_ips:
                inspect_h = self.agent_inspect[compute_ip]
                if inspect_h.get_vna_active_route(
                        vrf_id=self.agent_vrf_id[vn_fq_name],
                        ip=self.vm_ip_dict[vn_fq_name],
                        prefix='32') is not None:
                    self.logger.warn(
                        "Route for VM %s, IP %s is still seen in agent %s " %
                        (self.vm_name, self.vm_ip_dict[vn_fq_name], compute_ip))
                    self.verify_vm_not_in_agent_flag = self.verify_vm_not_in_agent_flag and False
                    result = result and False
            if result:
                self.logger.info(
                    "VM %s routes are removed "
                    "in all agent nodes" % (self.vm_name))
        return result


    def get_control_nodes(self):
        bgp_ips = {}
        vm_host = self.vm_node_ip
        try:
            bgp_ips = self.inputs.build_compute_to_control_xmpp_connection_dict(
                self.connections)
            bgp_ips = bgp_ips[vm_host]
        except Exception as e:
            self.logger.exception("Exception in get_control_nodes....")
        finally:
            return bgp_ips

    @retry(delay=5, tries=20)
    def verify_vm_in_control_nodes(self):
        ''' Validate routes are created in Control-nodes for this VM

        '''
        self.vm_in_cn_flag = True
        self.ri_names = {}
        if (len(self.inputs.bgp_ips) <= 2):
            self.bgp_ips = []
            self.bgp_ips = self.inputs.bgp_ips[:]
        else:
            self.bgp_ips = self.get_control_nodes()

        if self.inputs.bgp_ips_curr:
            bgp_ips = self.inputs.bgp_ips_curr
        else:
            bgp_ips = self.inputs.bgp_ips

        for vn_fq_name in self.vn_fq_names:
            fw_mode = self.vnc_lib_fixture.get_forwarding_mode(vn_fq_name)
#            for cn in self.inputs.bgp_ips:
            for cn in self.bgp_ips:
                vn_name = vn_fq_name.split(':')[-1]
                ri_name = vn_fq_name + ':' + vn_name
                self.ri_names[vn_fq_name] = ri_name
                if fw_mode != unicode('l2'):
                    # Check for VM route in each control-node
                    #vn_name= vn_fq_name.split(':')[-1]
                    #ri_name= vn_fq_name + ':' + vn_name
                    #self.ri_names[vn_fq_name]= ri_name
                    if ':' in self.vm_ip_dict[vn_fq_name] :
                        cn_routes = self.cn_inspect[cn].get_cn_ipv6_route_table_entry(
                        ri_name=ri_name, prefix=self.vm_ip_dict[vn_fq_name] + '/128')
                    else:
 
                        cn_routes = self.cn_inspect[cn].get_cn_route_table_entry(
                                    ri_name=ri_name, prefix=self.vm_ip_dict[vn_fq_name] + '/32')
                    if not cn_routes:
                        with self.printlock:
                            self.logger.warn(
                                'No route found for VM IP %s in Control-node %s' %
                                (self.vm_ip_dict[vn_fq_name], cn))
                        self.vm_in_cn_flag = self.vm_in_cn_flag and False
                        return False
                    if cn_routes[0]['next_hop'] != self.vm_node_data_ip:
                        with self.printlock:
                            self.logger.warn(
                                'Next hop for VM %s is not set to %s in Control-node'
                                ' Route table' % (self.vm_name, self.vm_node_data_ip))
                        self.vm_in_cn_flag = self.vm_in_cn_flag and False
                        return False
                    # Label in agent and control-node should match
                    if cn_routes[0]['label'] != self.agent_label[vn_fq_name]:
                        with self.printlock:
                            self.logger.warn(
                                "Label for VM %s differs between Control-node "
                                "%s and Agent, Expected: %s, Seen: %s" %
                                (self.vm_name, cn, self.agent_label[
                                    vn_fq_name],
                                 cn_routes[0]['label']))
                            self.logger.debug(
                                'Route in CN %s : %s' % (cn, str(cn_routes)))
                        self.vm_in_cn_flag = self.vm_in_cn_flag and False
                        return False

                self.logger.info(
                    'Starting all layer2 verification in %s Control Node' % (cn))
                # L2 verification

#                prefix = self.mac_addr[vn_fq_name] + \
#                    ',' + self.vm_ip_dict[vn_fq_name] + '/32'
                prefix = self.mac_addr[vn_fq_name] + \
                    ',' + self.vm_ip_dict[vn_fq_name]
                # Chhandak
                # Computing the ethernet tag for prefix here, format is  EncapTyepe-IP(0Always):0-VXLAN-MAC,IP
                if vn_fq_name in self.agent_vxlan_id.keys():
                    ethernet_tag = "2-0:0" + '-' + self.agent_vxlan_id[vn_fq_name]
                else:
                    ethernet_tag ="2-0:0-0"
                prefix = ethernet_tag + '-' + prefix
                #currently mac + ipv6 doesnot supprt so for ipv6 address it will return true
                if ':' in self.vm_ip_dict[vn_fq_name]  :
                    self.logger.info(
                    'Skipping the layer 2 verification of %s control node for ipv6 network since its not supporting' % (cn))
                    return True
                cn_l2_routes = self.cn_inspect[cn].get_cn_route_table_entry(
                    ri_name=ri_name, prefix=prefix, table='evpn.0')
                if not cn_l2_routes:
                    self.logger.warn(
                        'No layer2 route found for VM MAC %s in Control-node %s'
                        '' % (self.mac_addr[vn_fq_name], cn))
                    self.vm_in_cn_flag = self.vm_in_cn_flag and False
                    return False
                else:
                    self.logger.info(
                        'Layer2 route found for VM MAC %s in \
                        Control-node %s' % (self.mac_addr[vn_fq_name], cn))
                if cn_l2_routes[0]['next_hop'] != self.vm_node_data_ip:
                    self.logger.warn(
                        "Next hop for VM %s is not set to %s in "
                        "Control-node Route table" % (self.vm_name,
                                                      self.vm_node_data_ip))
                    self.vm_in_cn_flag = self.vm_in_cn_flag and False
                    return False

                if cn_l2_routes[0]['tunnel_encap'][0] == 'vxlan':
                    # Label in agent and control-node should match
                    if cn_l2_routes[0]['label'] != self.agent_vxlan_id[vn_fq_name]:
                        with self.printlock:
                            self.logger.warn(
                                "L2 Label for VM %s differs between Control-node "
                                "%s and Agent, Expected: %s, Seen: %s" %
                                (self.vm_name, cn, self.agent_vxlan_id[
                                    vn_fq_name],
                                 cn_l2_routes[0]['label']))
                            self.logger.debug(
                                'Route in CN %s : %s' % (cn, str(cn_l2_routes)))
                        self.vm_in_cn_flag = self.vm_in_cn_flag and False
                        return False
                    else:
                        with self.printlock:
                            self.logger.info(
                                "L2 Label for VM %s same between Control-node "
                                "%s and Agent, Expected: %s, Seen: %s" %
                                (self.vm_name, cn,
                                 self.agent_vxlan_id[vn_fq_name],
                                 cn_l2_routes[0]['label']))
                else:
                    # Label in agent and control-node should match
                    if cn_l2_routes[0]['label'] != self.agent_l2_label[vn_fq_name]:
                        with self.printlock:
                            self.logger.warn(
                                "L2 Label for VM %s differs between Control-node "
                                "%s and Agent, Expected: %s, Seen: %s" %
                                (self.vm_name, cn, self.agent_l2_label[
                                    vn_fq_name],
                                 cn_l2_routes[0]['label']))
                            self.logger.debug(
                                'Route in CN %s : %s' % (cn, str(cn_l2_routes)))
                        self.vm_in_cn_flag = self.vm_in_cn_flag and False
                        return False
                    else:
                        with self.printlock:
                            self.logger.info(
                                "L2 Label for VM %s same between Control-node "
                                "%s and Agent, Expected: %s, Seen: %s" %
                                (self.vm_name, cn,
                                 self.agent_l2_label[vn_fq_name],
                                 cn_l2_routes[0]['label']))

            # end for
        self.vm_in_cn_flag = self.vm_in_cn_flag and True
        with self.printlock:
            self.logger.info(
                "Verification in Control-nodes for VM %s passed" % (self.vm_name))
        return True
    # end verify_vm_in_control_nodes

    @retry(delay=2, tries=25)
    def verify_vm_not_in_control_nodes(self):
        ''' Validate that routes for VM is removed in control-nodes.

        '''
        result = True
        self.verify_vm_not_in_control_nodes_flag = True

        # updating the bgp_ips for ha testing.
        if self.inputs.bgp_ips_curr:
            bgp_ips = self.inputs.bgp_ips_curr
        else:
            bgp_ips = self.inputs.bgp_ips

        for vn_fq_name in self.vn_fq_names:
#            for cn in self.inputs.bgp_ips:
            for cn in bgp_ips:
                # Check for VM route in each control-node
                routing_instance = self.cn_inspect[cn].get_cn_routing_instance(
                    ri_name=self.ri_names[vn_fq_name])
                cn_routes = self.cn_inspect[cn].get_cn_route_table_entry(
                    ri_name=self.ri_names[vn_fq_name],
                    prefix=self.vm_ip_dict[vn_fq_name] + '/32')
                if cn_routes is not None:
                    with self.printlock:
                        self.logger.warn(
                            "Control-node %s still seems to have route for VMIP %s" %
                            (cn, self.vm_ip_dict[vn_fq_name]))
                    self.verify_vm_not_in_control_nodes_flag = self.verify_vm_not_in_control_nodes_flag and False
                    result = result and False
            # end for
        if result:
            with self.printlock:
                self.logger.info(
                    "Routes for VM %s is removed in all control-nodes"
                    % (self.vm_name))
        return result
    # end verify_vm_not_in_control_nodes

    def _get_ops_intf_index(self, ops_intf_list, vn_fq_name):
        for intf in ops_intf_list:
            if intf['virtual_network'] == vn_fq_name:
                return ops_intf_list.index(intf)
        return None

    @retry(delay=2, tries=15)
    def verify_vm_in_opserver(self):
        ''' Verify VM objects in Opserver.
        '''
        self.logger.info("Verifying the vm in opserver")
        result = True
        self.vm_in_op_flag = True
        for ip in self.inputs.collector_ips:
            self.logger.info("Verifying in collector %s ..." % (ip))
            self.ops_vm_obj = self.ops_inspect[ip].get_ops_vm(self.vm_id)
            ops_intf_list = self.ops_vm_obj.get_attr('Agent', 'interface_list')
            if not ops_intf_list:
                self.logger.warn(
                    'Failed to get VM %s, ID %s info from Opserver' %
                    (self.vm_name, self.vm_id))
                self.vm_in_op_flag = self.vm_in_op_flag and False
                return False
            for vn_fq_name in self.vn_fq_names:
                vm_in_pkts = None
                vm_out_pkts = None
                fw_mode = self.vnc_lib_fixture.get_forwarding_mode(vn_fq_name)
                ops_index = self._get_ops_intf_index(ops_intf_list, vn_fq_name)
                if ops_index is None:
                    self.logger.error(
                        'VN %s is not seen in opserver for VM %s' %
                        (vn_fq_name, self.vm_id))
                    self.vm_in_op_flag = self.vm_in_op_flag and False
                    return False
                ops_data = ops_intf_list[ops_index]
                if fw_mode != unicode('l2'):
                    if ':' in self.vm_ip_dict[vn_fq_name] :
                        op_data=ops_data['ip6_address']
                    else:
                        op_data=ops_data['ip_address']
                    if self.vm_ip_dict[vn_fq_name] != op_data :
                        self.logger.warn(
                            "VM %s IP Address of %s not in Opserver VM view"
                            " " % (self.vm_name, self.vm_ip_dict[vn_fq_name]))
                        self.vm_in_op_flag = self.vm_in_op_flag and False
                        result = result and False
                # end if
                self.ops_vm_obj = self.ops_inspect[ip].get_ops_vm(self.vm_id)
        # end if
        self.logger.info("Verifying vm in vn uve")
        for intf in ops_intf_list:
            virtual_network = intf['virtual_network']
            ip_address = intf['ip_address']
            intf_name = intf['name']
            self.logger.info("vm uve shows interface as %s" % (intf_name))
            if fw_mode != unicode('l2'):
                self.logger.info("vm uve shows ip address as %s" %
                                 (ip_address))
            self.logger.info("vm uve shows virtual netowrk as %s" %
                             (virtual_network))
            vm_in_vn_uve = self.analytics_obj.verify_vn_uve_for_vm(
                vn_fq_name=virtual_network, vm=self.vm_id)
        if vm_in_vn_uve:
            self.vm_in_op_flag = self.vm_in_op_flag and True
            result = result and True
        else:
            self.vm_in_op_flag = self.vm_in_op_flag and False
            result = result and False

        # Verifying vm in vrouter-uve
        self.logger.info("Verifying vm in vrouter uve")
        computes = []
        for ip in self.inputs.collector_ips:
            self.logger.info("Getting info from collector %s.." % (ip))
            agent_host = self.analytics_obj.get_ops_vm_uve_vm_host(
                ip, self.vm_id)
            if agent_host not in computes:
                computes.append(agent_host)
        if (len(computes) > 1):
            self.logger.warn(
                "Inconsistancy - collectors dont have consistant info for vm uve")
            self.vm_in_op_flag = self.vm_in_op_flag and False
            result = result and False
        self.logger.info("vm uve shows vrouter as %s" % (computes))

        for compute in computes:
            vm_in_vrouter = self.analytics_obj.verify_vm_list_in_vrouter_uve(
                vm_uuid=self.vm_id, vrouter=compute)
            if vm_in_vrouter:
                self.vm_in_op_flag = self.vm_in_op_flag and True
                result = result and True
            else:
                self.vm_in_op_flag = self.vm_in_op_flag and False
                result = result and False
        # Verify tap interface/conected networks in vrouter uve
        self.logger.info("Verifying vm tap interface/vn in vrouter uve")
        self.vm_host = self.inputs.host_data[self.vm_node_ip]['name']
        self.tap_interfaces = self.agent_inspect[
            self.vm_node_ip].get_vna_tap_interface_by_vm(vm_id=self.vm_id)
        for intf in self.tap_interfaces:
            self.tap_interface = intf['config_name']
            self.logger.info("expected tap interface of vm uuid %s is %s" %
                             (self.vm_id, self.tap_interface))
            self.logger.info("expected virtual network  of vm uuid %s is %s" %
                             (self.vm_id, intf['vn_name']))
            is_tap_thr = self.analytics_obj.verify_vm_list_in_vrouter_uve(
                vm_uuid=self.vm_id,
                vn_fq_name=intf['vn_name'],
                vrouter=self.vm_host,
                tap=self.tap_interface)

            if is_tap_thr:
                self.vm_in_op_flag = self.vm_in_op_flag and True
                result = result and True
            else:
                self.vm_in_op_flag = self.vm_in_op_flag and False
                result = result and False

        if self.analytics_obj.verify_vm_link(self.vm_id):
            self.vm_in_op_flag = self.vm_in_op_flag and True
            result = result and True
        else:
            self.vm_in_op_flag = self.vm_in_op_flag and False
            result = result and False

        if result:
            self.logger.info("VM %s validation in Opserver passed" %
                             (self.vm_name))
        else:
            self.logger.warn('VM %s validation in Opserver failed' %
                             (self.vm_name))
        return result

    # end verify_vm_in_opserver

    @retry(delay=3, tries=15)
    def tcp_data_transfer(self, localip, fip, datasize=1024):
        '''Send data file from a VM to an IP specified.

        This method logs into the VM from the host machine using ssh and sends a
        data file to an IP.
        '''
        output = ''
        url = 'http://%s/' % fip
        cmd = 'curl -I -m 25 --connect-timeout 25 %s' % url
        self.run_cmd_on_vm(cmds=[cmd])
        output = self.return_output_values_list[0]
        if '200 OK' not in output:
            self.logger.warn("Tcp data transfer to IP %s from VM %s"
                             " failed" % (fip, self.vm_name))
            return False
        else:
            self.logger.info("Tcp data transfer to IP %s from VM %s"
                             " Passed" % (fip, self.vm_name))
        return True
    # end tcp_data_transfer

    def get_vrf_ids_accross_agents(self):
        vrfs = dict()
        try:
            for ip in self.inputs.compute_ips:
                inspect_h = self.agent_inspect[ip]
                dct = dict()    
                for vn_fq_name in self.vn_fq_names:
                    vrf_id = inspect_h.get_vna_vrf_id(vn_fq_name)
                    if vrf_id:
                        dct.update({vn_fq_name:vrf_id[0]})
                if dct:
                    vrfs[ip] = dct
        except Exception as e:
            print 'Got exceptionas %s'%e
        finally:
            return vrfs

    def cleanUp(self):
        super(VMFixture, self).cleanUp()
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            if self.inputs.is_gui_based_config():
                self.webui.delete_vm(self)
            else:
                self.vrfs = dict()
                self.vrfs = self.get_vrf_ids_accross_agents()
                for vm_obj in self.vm_objs:
                    for sec_grp in self.sg_ids:
                        self.logger.info(
                            "Removing the security group from VM %s" % (vm_obj.name))
                        self.remove_security_group(sec_grp)
                    self.logger.info("Deleting the VM %s" % (vm_obj.name))
                    self.nova_fixture.delete_vm(vm_obj)
                    self.vm_objs.remove(self.vm_obj)
                time.sleep(5)
            # Not expected to do verification when self.count is > 1, right now
            if self.verify_is_run:
                 assert self.verify_vm_not_in_api_server()
                 assert self.verify_vm_not_in_agent()
                 assert self.verify_vm_not_in_control_nodes()
                 assert self.verify_vm_not_in_nova()

                 assert self.verify_vm_flows_removed()
                 for vn_fq_name in self.vn_fq_names:
                    self.analytics_obj.verify_vm_not_in_opserver(self.vm_id, 
                                   self.inputs.host_data[self.vm_node_ip]['name'], vn_fq_name)

                # Trying a workaround for Bug 452
            # end if
        else:
            self.logger.info('Skipping the deletion of VM %s' %
                             (self.vm_name))
    # end cleanUp

    @retry(delay=2, tries=25)
    def verify_vm_not_in_nova(self):
        result = True
        self.verify_vm_not_in_nova_flag = True
        # In environments which does not have mysql token file, skip the check
        if not self.inputs.mysql_token:
            return result
        for vm_obj in self.vm_objs:
            result = result and self.nova_fixture.is_vm_deleted_in_nova_db(
                vm_obj, self.inputs.openstack_ip)
            self.verify_vm_not_in_nova_flag = self.verify_vm_not_in_nova_flag and result
        return result
    # end verify_vm_not_in_nova

    def tftp_file_to_vm(self, file, vm_ip):
        '''Do a tftp of the specified file to the specified VM

        '''
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        try:
            self.nova_fixture.put_key_file_to_host(self.vm_node_ip)
            with hide('everything'):
                with settings(
                    host_string='%s@%s' % (
                        host['username'], self.vm_node_ip),
                    password=host['password'],
                        warn_only=True, abort_on_prompts=False):
                    key_file = self.nova_fixture.tmp_key_file
                    if ':' in vm_ip :
                       i= 'tftp -m binary -v %s -c put %s' %(vm_ip,file)
                    else:

                       i = 'timeout 20 atftp -p -r %s -l %s %s' % (file,
                                                                file, vm_ip)
                    self.run_cmd_on_vm(cmds=[i])
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying to tftp the file')
    # end tftp_file_to_vm

    def scp_file_to_vm(self, file, vm_ip, dest_vm_username='ubuntu'):
        '''Do a scp of the specified file to the specified VM

        '''
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''

        # We need to retry following section and scale it up if required (for slower VMs
        # TODO: Use @retry annotation instead
        if "TEST_DELAY_FACTOR" in os.environ:
            delay_factor = os.environ.get("TEST_DELAY_FACTOR")
        else:
            delay_factor = "1.0"
        timeout = math.floor(40 * float(delay_factor))

        try:
            self.nova_fixture.put_key_file_to_host(self.vm_node_ip)
            with hide('everything'):
                with settings(
                    host_string='%s@%s' % (
                        host['username'], self.vm_node_ip),
                    password=host['password'],
                        warn_only=True, abort_on_prompts=False):
                    key_file = self.nova_fixture.tmp_key_file
                    self.get_rsa_to_vm()
                    if ':' in vm_ip :
                        dest_vm_username='root'
                        i = 'scp -o StrictHostKeyChecking=no  -i id_rsa %s %s@[%s]:/root/' % (
                         file, dest_vm_username, vm_ip)
                    else:
                        i = 'timeout %d scp -o StrictHostKeyChecking=no -i id_rsa %s %s@%s:' % (
                            timeout, file, dest_vm_username, vm_ip)
                    cmd_outputs = self.run_cmd_on_vm(cmds=[i])
                    self.logger.debug(cmd_outputs)
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying to scp the file ')
    # end scp_file_to_vm

    def put_pub_key_to_vm(self):
        self.logger.debug('Copying public key to VM %s' % (self.vm_name))
        self.nova_fixture.put_key_file_to_host(self.vm_node_ip)
        auth_file = '.ssh/authorized_keys'
        self.run_cmd_on_vm(['mkdir -p ~/.ssh'])
        host = self.inputs.host_data[self.vm_node_ip]
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (host['username'], self.vm_node_ip),
                password=host['password'],
                    warn_only=True, abort_on_prompts=False):
                key_file = self.nova_fixture.tmp_key_file
                fab_put_file_to_vm(host_string='%s@%s' % (
                    self.vm_username, self.local_ip),
                    password=self.vm_password,
                    src='/tmp/id_rsa.pub', dest='/tmp/')
        cmds = [
            'cat /tmp/id_rsa.pub >> ~/%s' % (auth_file),
            'chmod 600 ~/%s' % (auth_file),
            'cat /tmp/id_rsa.pub >> /root/%s' % (auth_file),
            'chmod 600 /root/%s' % (auth_file),
        '''sed -i -e 's/no-port-forwarding.*sleep 10\" //g' ~root/.ssh/authorized_keys''']
        self.run_cmd_on_vm(cmds, as_sudo=True)
    
    @retry(delay=10, tries=5)
    def check_file_transfer(self, dest_vm_fixture, mode='scp', size='100', fip=None, expectation= True):
        '''
        Creates a file of "size" bytes and transfers to the VM in dest_vm_fixture using mode scp/tftp
        '''
        filename = 'testfile'
        if fip:
           dest_vm_ip = fip
        else:
           dest_vm_ip = dest_vm_fixture.vm_ip
        for vm_ipv6 in dest_vm_fixture.vm_ips :
            if ':' in vm_ipv6 :
                dest_vm_ip= vm_ipv6
        # Create file
        cmd = 'dd bs=%s count=1 if=/dev/zero of=%s' % (size, filename)
        self.run_cmd_on_vm(cmds=[cmd])

        # Copy file
        if mode == 'scp':
            dest_vm_fixture.run_cmd_on_vm(
                cmds=['cp -f ~root/.ssh/authorized_keys ~/.ssh/'], as_sudo=True)
            self.scp_file_to_vm(filename, vm_ip=dest_vm_ip)
        elif mode == 'tftp':
            # Create the file on the remote machine so that put can be done
            dest_vm_fixture.run_cmd_on_vm(
                cmds=['sudo touch /var/lib/tftpboot/%s' % (filename),
                      'sudo chmod 777 /var/lib/tftpboot/%s' % (filename)])
            self.tftp_file_to_vm(filename, vm_ip=dest_vm_ip)
        else:
            self.logger.error('No transfer mode specified!!')
            return False
        self.run_cmd_on_vm(cmds=['sync'])

        # Verify if file size is same
        if mode == 'scp':
            out_dict = dest_vm_fixture.run_cmd_on_vm(
                cmds=['ls -l %s' % (filename)])
        elif mode == 'tftp':
            out_dict = dest_vm_fixture.run_cmd_on_vm(
                cmds=['ls -l /var/lib/tftpboot/%s' % (filename)])
        if size in out_dict.values()[0]:
            self.logger.info('File of size %s is trasferred successfully to \
                    %s by %s ' % (size, dest_vm_ip, mode))
            if not expectation:
                return False
            else:
                return True
        else:
            self.logger.warn('File of size %s is not trasferred fine to %s \
                    by %s' % (size, dest_vm_ip, mode))
            if not expectation:
                return True
            else:
                return False
    # end check_file_transfer

    def get_rsa_to_vm(self):
        '''Get the rsa file to the VM from the agent

        '''
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        try:
            self.nova_fixture.put_key_file_to_host(self.vm_node_ip)
            with hide('everything'):
                with settings(
                    host_string='%s@%s' % (
                        host['username'], self.vm_node_ip),
                    password=host['password'],
                        warn_only=True, abort_on_prompts=False):
                    key_file = self.nova_fixture.tmp_key_file
                    fab_put_file_to_vm(host_string='%s@%s' % (
                        self.vm_username, self.local_ip),
                        password=self.vm_password,
                        src=key_file, dest='~/')
                    self.run_cmd_on_vm(cmds=['chmod 600 id_rsa'])

        except Exception, e:
            self.logger.exception(
                'Exception occured while trying to get the rsa file to the \
                 VM from the agent')
    # end get_rsa_to_vm

    def run_cmd_on_vm(self, cmds=[], as_sudo=False):
        '''run cmds on VM

        '''
        self.return_output_cmd_dict = {}
        self.return_output_values_list = []
        cmdList = cmds
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        try:
            self.nova_fixture.put_key_file_to_host(self.vm_node_ip)
            fab_connections.clear()
            with hide('everything'):
                with settings(
                    host_string='%s@%s' % (host['username'], self.vm_node_ip),
                    password=host['password'],
                        warn_only=True, abort_on_prompts=False):
                    key_file = self.nova_fixture.tmp_key_file
                    for cmd in cmdList:
                        self.logger.debug('Running Cmd on %s: %s' % (
                            self.vm_node_ip, cmd))
                        output = run_fab_cmd_on_node(
                            host_string='%s@%s' % (
                                self.vm_username, self.local_ip),
                            password=self.vm_password,
                            cmd=cmd,
                            as_sudo=as_sudo)
                        self.logger.debug(output)
                        self.return_output_values_list.append(output)
                    self.return_output_cmd_dict = dict(
                        zip(cmdList, self.return_output_values_list))
            return self.return_output_cmd_dict
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying ping from VM ')
            return self.return_output_cmd_dict

    def get_vm_ip_from_vm(self, vn_fq_name=None):
        ''' Get VM IP from Ifconfig output executed on VM
        '''
        vm_ip = None
        if not vn_fq_name:
            vn_fq_name = self.vn_fq_names[0]
        cmd = "ifconfig | grep %s" % (self.tap_intf[vn_fq_name]['ip_addr'])
        self.run_cmd_on_vm(cmds=[cmd])
        output = self.return_output_cmd_dict[cmd]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        if match:
            vm_ip = match.group(1)
        return vm_ip
    # end def

    def wait_till_vm_is_up(self):
        status = self.wait_till_vm_up()
        if type(status) == tuple:
            return status[0]
        elif type(status) == bool:
            return status

    def wait_till_vm_is_active(self):
        status = self.nova_fixture.wait_till_vm_is_active(self.vm_obj)
        if type(status) == tuple:
            if status[1] in 'ERROR':
                return False
            elif status[1] in 'ACTIVE':
                return True
        elif type(status) == bool:
            return status

    @retry(delay=3, tries=10)
    def wait_till_vm_up(self):
        vm_status = self.nova_fixture.wait_till_vm_is_active(self.vm_obj)
        if type(vm_status) == tuple:
            if vm_status[1] in 'ERROR':
                self.logger.warn("VM in error state. Asserting...")
                return (False, 'final')
#            assert False

            if vm_status[1] != 'ACTIVE':
                result = result and False
                return result
        elif type(vm_status) == bool:
            return (vm_status, 'final')
            
        result = self.verify_vm_launched()
        #console_check = self.nova_fixture.wait_till_vm_is_up(self.vm_obj)
        #result = result and self.nova_fixture.wait_till_vm_is_up(self.vm_obj)
        # if not console_check :
        #    import pdb; pdb.set_trace()
        #    self.logger.warn('Console logs didnt give enough info on bootup')
        self.vm_obj.get()
        result = result and self._gather_details()
        result = result and self.wait_for_ssh_on_vm()
        if not result:
            self.logger.error('VM %s does not seem to be fully up' % (
                              self.vm_name))
            return result
        return True
    # end wait_till_vm_is_up
   
    def scp_file_transfer_cirros(self, dest_vm_fixture, fip = None, size = '100'):
        '''
        Creates a file of "size" bytes and transfers to the VM in dest_vm_fixture using mode scp/tftp
        '''
        filename='testfile'
        dest_vm_ip = dest_vm_fixture.vm_ip
        import pexpect
        # Create file
        cmd = 'dd bs=%s count=1 if=/dev/zero of=%s' %(size, filename)
        self.run_cmd_on_vm(cmds=[cmd])
        host = self.inputs.host_data[self.vm_node_ip]

        if "TEST_DELAY_FACTOR" in os.environ:
            delay_factor = os.environ.get("TEST_DELAY_FACTOR")
        else:
            delay_factor = "1.0"
        timeout = math.floor(40 * float(delay_factor))

        with settings(host_string='%s@%s' % (host['username'], self.vm_node_ip),
                                             password=host['password'],
                                             warn_only=True, abort_on_prompts=False):
            handle = pexpect.spawn('ssh -F /dev/null -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null %s@%s' %(self.vm_username, self.local_ip))
            handle.timeout = int(timeout)
            i = handle.expect(['\$ ', 'password:'])
            if i == 0:
                pass
            if i == 1:
                handle.sendline('cubswin:)')
                handle.expect('\$ ')
            if fip:
                handle.sendline('scp %s %s@%s:~/.' %(filename, dest_vm_fixture.vm_username, fip))
            else:
                handle.sendline('scp %s %s@%s:~/.' %(filename, dest_vm_fixture.vm_username, dest_vm_fixture.vm_ip))
            i = handle.expect(['Do you want to continue connecting', '[P,p]assword'])
            if i == 0:
                handle.sendline('y')
                handle.expect('[P,p]assword')
                handle.sendline('cubswin:)')
            elif i == 1:
                handle.sendline('cubswin:)')
            else:
                self.logger.warn('scp file to VM failed')
            out_dict = dest_vm_fixture.run_cmd_on_vm(cmds=['ls -l %s' %(filename)])
            if size in out_dict.values()[0]:
                self.logger.info('File of size %s is trasferred successfully to \
                                  %s ' %(size, dest_vm_fixture.vm_name))
                return True
            else:
                self.logger.warn('File of size %s is not trasferred fine to %s \
                                 !! Pls check logs' % (size, dest_vm_fixture.vm_name))
                return False

    #end scp_file_transfer_cirros

 
    def wait_till_vm_boots(self):
        return self.nova_fixture.wait_till_vm_is_up(self.vm_obj)

    def get_console_output(self):
        return self.vm_obj.get_console_output()

    @retry(delay=5, tries=20)
    def wait_for_ssh_on_vm(self):
        self.logger.info('Waiting to SSH to VM %s, IP %s' % (self.vm_name,
                                                             self.vm_ip))

        # Check if ssh from compute node to VM works(with retries)
        cmd = 'fab -u %s -p "%s" -H %s -D -w --hide status,user,running verify_socket_connection:22' % (
            self.vm_username, self.vm_password, self.local_ip)
        output = self.inputs.run_cmd_on_server(self.vm_node_ip, cmd,
                                               self.inputs.host_data[
                                                   self.vm_node_ip][
                                                   'username'],
                                               self.inputs.host_data[self.vm_node_ip]['password'])
        #output = remove_unwanted_output(output)

        if 'True' in output:
            self.logger.info('VM %s is ready for SSH connections ' % (
                self.vm_name))
            return True
        else:
            self.logger.error('VM %s is NOT ready for SSH connections ' % (
                self.vm_name))
            return False
    # end wait_for_ssh_on_vm

    def get_vm_ipv6_addr_from_vm(self, intf='eth0', addr_type='link'):
        ''' Get VM IPV6 from Ifconfig output executed on VM
        '''
        vm_ipv6 = None
        cmd = "ifconfig %s| awk '/inet6/ {print $3}'" % (intf)
        self.run_cmd_on_vm(cmds=[cmd])
        if cmd in self.return_output_cmd_dict.keys():
            output = self.return_output_cmd_dict[cmd]
            if (addr_type == 'link'):
                match = re.search('inet6 addr:(.+?) Scope:Link', output)
            elif (addr_type == 'global'):
                match = re.search('inet6 addr:(.+?) Scope:Global', output)
            else:
                match = None

            if match:
                vm_ipv6 = match.group(1)
        return vm_ipv6

    def get_active_controller(self):
        ''' Get the active contol node.
        '''
        active_controller = None
        inspect_h = self.agent_inspect[self.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes' \
                    and entry['state'] == 'Established':
                active_controller = entry['controller_ip']
        if not active_controller:
            self.logger.error('Active controlloer is not found')
        return active_controller

    def install_pkg(self, pkgname="Traffic"):
        if pkgname == "Traffic":
            self.logger.info("Skipping installation of traffic package on VM")
            return True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        pkgsrc = PkgHost(self.inputs.cfgm_ips[0], self.vm_node_ip,
                         username, password)
        self.nova_fixture.put_key_file_to_host(self.vm_node_ip)
        key = self.nova_fixture.tmp_key_file
        pkgdst = PkgHost(self.local_ip, key=key, user=self.vm_username,
                         password=self.vm_password)
        fab_connections.clear()

        assert build_and_install(pkgname, pkgsrc, pkgdst, self.logger)

    @retry(delay=2, tries=15)
    def verify_vm_flows_removed(self):
        cmd = 'flow -l '
        result = True
        # TODO Change the logic so that check is not global(causes problems
        # when run in parallel if same IP is across Vns or projects)
        return result
        self.vm_flows_removed_flag = True
        output = self.inputs.run_cmd_on_server(self.vm_node_ip, cmd,
                                               self.inputs.host_data[
                                                   self.vm_node_ip][
                                                   'username'],
                                               self.inputs.host_data[self.vm_node_ip]['password'])

        if '%s:' % (self.vm_ip) in output:
            self.logger.warn(
                "One or more flows still present on Compute node after VM delete : %s" % (output))
            result = False
        else:
            self.logger.info("All flows for the VM deleted on Compute node")
        self.vm_flows_removed_flag = self.vm_flows_removed_flag and result
        return result
    # end verify_vm_flows_removed

    def provision_static_route(
            self,
            prefix='111.1.0.0/16',
            tenant_name=None,
            api_server_ip='127.0.0.1',
            api_server_port='8082',
            oper='add',
            virtual_machine_interface_id='',
            route_table_name='my_route_table',
            user='admin',
            password='contrail123'):

        if not tenant_name:
            tenant_name = self.inputs.stack_tenant
        cmd = "python /opt/contrail/utils/provision_static_route.py --prefix %s \
                --tenant_name %s  \
                --api_server_ip %s \
                --api_server_port %s\
                --oper %s \
                --virtual_machine_interface_id %s \
                --user %s\
                --password %s\
                --route_table_name %s" % (prefix,
                                          tenant_name,
                                          api_server_ip,
                                          api_server_port,
                                          oper,
                                          virtual_machine_interface_id,
                                          user,
                                          password,
                                          route_table_name)
        args = shlex.split(cmd)
        process = Popen(args, stdout=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            self.logger.warn("Route could not be created , err : \n %s" %
                             (stderr))
        else:
            self.logger.info("%s" % (stdout))

    def _gather_details(self):
        self.cs_vmi_objs = {}
        self.cs_vmi_obj = {}
        self.vm_id = self.vm_objs[0].id
        # Figure out the local metadata IP of the VM reachable from host
        nova_host = self.inputs.host_data[
            self.nova_fixture.get_nova_host_of_vm(self.vm_obj)]
        self.vm_node_ip = nova_host['host_ip']
        self.vm_node_data_ip = nova_host['host_data_ip']
        inspect_h = self.agent_inspect[self.vm_node_ip]

        cfgm_ip = self.inputs.cfgm_ips[0]
        api_inspect = self.api_s_inspects[cfgm_ip]
        self.cs_vmi_objs[cfgm_ip] = api_inspect.get_cs_vmi_of_vm(self.vm_id)
        for vmi_obj in self.cs_vmi_objs[cfgm_ip]:
            vmi_vn_fq_name = ':'.join(
                vmi_obj['virtual-machine-interface']['virtual_network_refs'][0]['to'])
            self.cs_vmi_obj[vmi_vn_fq_name] = vmi_obj

        self.local_ip = False
        for vn_fq_name in self.vn_fq_names:
            fw_mode = self.vnc_lib_fixture.get_forwarding_mode(vn_fq_name)
            (domain, project, vn) = vn_fq_name.split(':')
            vna_tap_id = inspect_h.get_vna_tap_interface_by_vmi(
                vmi_id=self.cs_vmi_obj[vn_fq_name][
                    'virtual-machine-interface']['uuid'])
            self.tap_intf[vn_fq_name] = vna_tap_id[0]
            self.tap_intf[vn_fq_name] = inspect_h.get_vna_intf_details(
                self.tap_intf[vn_fq_name]['name'])[0]
            if fw_mode != unicode('l2'):
                if 'Active' not in self.tap_intf[vn_fq_name]['active']:
                    self.logger.warn('VMI %s status is not active, it is %s' % (
                        self.tap_intf[vn_fq_name]['name'],
                        self.tap_intf[vn_fq_name]['active']))
                    return False
            self.local_ips[vn_fq_name] = self.tap_intf[
                vn_fq_name]['mdata_ip_addr']
            if self.local_ips[vn_fq_name] != '0.0.0.0':
                if self.ping_vm_from_host(vn_fq_name) or self.ping_vm_from_host( vn_fq_name) :
                    self.local_ip= self.local_ips[vn_fq_name]
                elif not self.local_ip:
                    self.local_ip = self.local_ips[vn_fq_name]
 
                if self.ping_vm_from_host(vn_fq_name) or self.ping_vm_from_host(vn_fq_name):
                    self.local_ip = self.local_ips[vn_fq_name]
                elif not self.local_ip:
                    self.local_ip = self.local_ips[vn_fq_name]
        if '169.254' not in self.local_ip:
            self.logger.warn('VM metadata IP is not 169.254.x.x')
            return False
        return True
    # end _gather_details

    def interface_attach(self, port_id=None, net_id=None, fixed_ip=None):
        self.logger.info('Attaching port %s to VM %s' %
                         (port_id, self.vm_obj.name))
        return self.vm_obj.interface_attach(port_id, net_id, fixed_ip)

    def interface_detach(self, port_id):
        self.logger.info('Detaching port %s from VM %s' %
                         (port_id, self.vm_obj.name))
        return self.vm_obj.interface_detach(port_id)

    def reboot(self, type='SOFT'):
        self.vm_obj.reboot(type)

    def wait_till_vm_status(self, status='ACTIVE'):
        return self.nova_fixture.wait_till_vm_status(self.vm_obj, status)


# end VMFixture
class VMData(object):

    """ Class to store VM related data.
    """

    def __init__(self, name, vn_obj, image='ubuntu', project='admin', flavor='m1.tiny'):
        self.name = name
        self.vn_obj = vn_obj
        self.image = image
        self.project = project
        self.flavor = flavor


class MultipleVMFixture(fixtures.Fixture):

    """
    Fixture to handle creation, verification and deletion of multiple VMs.

    Deletion of the VM upon exit can be disabled by setting fixtureCleanup= 'no'
    in params file. If a VM with the vm_name is already present, it is not
    deleted upon exit. To forcefully clean them up, set fixtureCleanup= 'force'
    """

    def __init__(self, connections, vms=[], vn_objs=[], image_name='ubuntu',
                 vm_count_per_vn=2, flavor='contrail_flavor_small', project_name=None):
        """
        vms     : List of dictionaries of VMData objects.
        or
        vn_objs : List of tuples of VN name and VNfixture.obj returned by the
                  get_all_fixture method of MultipleVNFixture.

        """

        self.connections = connections
        self.nova_fixture = self.connections.nova_fixture
        if not project_name:
            project_name = connections.inputs.stack_tenant
        self.project_name = project_name
        self.vms = vms
        self.vm_count = vm_count_per_vn
        self.vn_objs = vn_objs
        self.flavor = flavor
        self.image_name = image_name
        self.inputs = self.connections.inputs
        self.logger = self.inputs.logger
    # end __init__

    def create_vms_in_vn(self, name, image, flavor, project, vn_obj):
        for c in range(self.vm_count):
            vm_name = '%s_vm_%s' % (name, c)
            try:
                vm_fixture = self.useFixture(VMFixture(image_name=image,
                                                       project_name=project, flavor=flavor, connections=self.connections,
                                                       vn_obj=vn_obj, vm_name=vm_name))
            except Exception, err:
                self.logger.error(err)
                self.logger.debug(traceback.format_exc())
                break
            else:
                self._vm_fixtures.append((vm_name, vm_fixture))

    def setUp(self):
        super(MultipleVMFixture, self).setUp()
        self._vm_fixtures = []
        if self.vms:
            for vm in vms:
                self.create_vms_in_vn(vm.name, vm.image, vm.flavor, vm.project,
                                      vm.vn_obj)
        elif self.vn_objs:
            for vn_name, vn_obj in self.vn_objs:
                self.create_vms_in_vn(vn_name, self.image_name, self.flavor,
                                      self.project_name, vn_obj)
        else:
            self.logger.error("One of vms, vn_objs is  required.")

    def verify_on_setup(self):
        # TODO
        # Not expected to do verification when self.count > 1

        created_vms = len(self._vm_fixtures)
        expected_vms = len(self.vms)
        if self.vn_objs:
            expected_vms = self.vm_count * len(self.vn_objs)

        if created_vms != expected_vms:
            return False

        result = True
        for vm_name, vm_fixture in self._vm_fixtures:
            result &= vm_fixture.verify_on_setup()

        return result

    def get_all_fixture(self):
        return self._vm_fixtures
