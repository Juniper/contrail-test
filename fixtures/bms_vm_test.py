import re
import time
import shlex
import shutil
import traceback
import threading
import tempfile
import fixtures
import socket
import paramiko
from collections import defaultdict
from fabric.api import env
from fabric.api import run
from fabric.state import output
from fabric.state import connections as fab_connections
from fabric.operations import get, put
from fabric.context_managers import settings, hide
from subprocess import Popen, PIPE

from ironicclient import exceptions as ironic_exc

from ipam_test import *
from vn_test import *
from tcutils.util import *
from tcutils.util import safe_run, safe_sudo
from contrail_fixtures import *
from tcutils.pkgs.install import PkgHost, build_and_install
from security_group import get_secgrp_id_from_name, list_sg_rules
from tcutils.tcpdump_utils import start_tcpdump_for_intf,\
    stop_tcpdump_for_intf
from tcutils.agent.vrouter_lib import *
from tcutils.fabutils import *
from tcutils.test_lib.contrail_utils import get_interested_computes
from interface_route_table_fixture import InterfaceRouteTableFixture
env.disable_known_hosts = True
try:
    from webui_test import *
except ImportError:
    pass

try:
    from vcenter_gateway import VcenterGatewayOrch
except ImportError:
    pass
#output.debug= True

#@contrail_fix_ext ()


class BmsLcmVMFixture(fixtures.Fixture):

    '''
    Fixture to handle creation, verification and deletion of VM.
    image_name : One of cirros, redmine-fe, redmine-be, ubuntu

    Deletion of the VM upon exit can be disabled by setting fixtureCleanup= 'no' in params file.
    If a VM with the vm_name is already present, it is not deleted upon exit. To forcefully clean them up, set fixtureCleanup= 'force'
    Vn object can be a single VN object(vn_obj) or a list of VN objects(vn_objs) but not both
    '''

    def __init__(self, connections, vm_name=None, vn_obj=None,
                 vn_objs=[],
                 image_name='ubuntu', subnets=[],bms_node_name=None,
                 flavor=None,
                 node_name=None, sg_ids=[], count=1, userdata=None,
                 port_ids=[], fixed_ips=[], zone=None, vn_ids=[], uuid=None,*args,**kwargs):
        self.connections = connections
        self.admin_connections = kwargs.get('admin_connections')
        self.inputs = self.connections.inputs
        self.logger = self.connections.logger
        self.api_s_inspects = self.connections.api_server_inspects
        self.api_s_inspect = self.connections.api_server_inspect
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.ops_inspect = self.connections.ops_inspects
        self.orch = kwargs.get('orch', self.connections.orch)
        self.quantum_h = self.connections.quantum_h
        self.vnc_lib_fixture = self.connections.vnc_lib_fixture
        self.vnc_lib_h = self.connections.get_vnc_lib_h()
        self.nova_h = self.connections.nova_h
        self.ironic_h = self.connections.ironic_h
        self.node_name = node_name
        self.zone = zone
        self.sg_ids = sg_ids
        self.count = count
        self.port_ids = port_ids
        self.fixed_ips = fixed_ips
        self.subnets = subnets
        self.image_name = self.inputs.get_ci_image(image_name) or image_name
        self.flavor = self.orch.get_default_image_flavor(self.image_name) or flavor
        self.project_name = connections.project_name
        self.project_id = connections.project_id
        self.domain_name = connections.domain_name
        self.vm_name = vm_name or get_random_name(self.project_name)
        self.vm_id = uuid
        self.ironic_node_id = uuid
        self.vm_obj = None
        self.vm_ips = list()
        self.vn_objs = list((vn_obj and [vn_obj]) or vn_objs or
                            [self.orch.get_vn_obj_from_id(x) for x in vn_ids])
        if self.inputs.is_ci_setup():
            cidrs = []
            for vn_obj in self.vn_objs:
                if vn_obj['network'].has_key('subnet_ipam'):
                    cidrs.extend(list(map(lambda obj: obj['subnet_cidr'],
                                          vn_obj['network']['subnet_ipam'])))
            if cidrs and get_af_from_cidrs(cidrs) != 'v4':
                raise v4OnlyTestException('Disabling v6 tests for CI')
        self.vn_names = [self.orch.get_vn_name(x) for x in self.vn_objs]
        self.vn_fq_names = [':'.join(self.vnc_lib_h.id_to_fq_name(self.orch.get_vn_id(x)))
                            for x in self.vn_objs]
        self.vn_ids = vn_ids
        if len(self.vn_objs) == 1:
            self.vn_name = self.vn_names[0]
            self.vn_fq_name = self.vn_fq_names[0]
        self.verify_is_run = False
        self.analytics_obj = self.connections.analytics_obj
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
        self.cs_vmi_obj = {}
        self.vm_launch_flag = True
        self.vm_in_api_flag = True
        self.vm_in_agent_flag = True
        self.vm_in_cn_flag = True
        self.vm_in_op_flag = True
        self.verify_vm_not_in_setup = True
        self.verify_vm_not_in_api_server_flag = True
        self.bms_node_name = bms_node_name
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
        self._vm_interface = {}
        self._vrf_ids = {}
        self._interested_computes = []
        self.created = False
        self.refresh = False
        self._vmi_ids = {}
        self.cfgm_ip = self.inputs.cfgm_ip
        self.collector_ip = self.inputs.collector_ip
    # end __init__


    def read(self):
        try:
          if not self.ironic_node_id:
            self.ironic_node_obj = self.ironic_h.obj.node.get(self.bms_node_name)
            self.ironic_node_id = self.ironic_node_obj.uuid
          else:
            self.ironic_node_obj = self.ironic_h.obj.node.get(self.bms_node_name)
        except Exception,e:
            self.ironic_node_obj = None 

    def setUp(self):
        super(BmsLcmVMFixture, self).setUp()

    def delete_ironic_node(self):
        if not self.ironic_node_id:
           self.read()
        if not self.ironic_node_obj:
           self.logger.info("Ironic node %s not present, skipping delete "%self.bms_node_name)
           return
      
        self.ironic_h.obj.node.delete(self.ironic_node_id)

    def create_ironic_port(self,port,mac_address,node_uuid,portgroup_uuid,pxe_enabled):
          self.ironic_h.obj.port.create(local_link_connection=port,\
					address=mac_address,node_uuid=node_uuid,\
					portgroup_uuid=portgroup_uuid,pxe_enabled=pxe_enabled)

    def create_ironic_portgroup(self,node_id,pg_name,mac_addr):

        try:
          pg_obj = self.ironic_h.obj.portgroup.get(pg_name)
        except ironic_exc.NotFound:
          pg_obj = None 
        if not pg_obj:
          try:
             pg_obj = self.ironic_h.obj.portgroup.create(mode="802.3ad",name=pg_name,\
                                       address=mac_addr,\
                                       node_uuid=node_id)
          except ironic_exc.Conflict,ex:
             self.logger.info(ex.message) # TO_FIX: handle so that this is not hit
          except Exception,ex:
             self.logger.info("ERROR: exception in creating PG")
             return

        self.portgroup_uuid = pg_obj.uuid

    def create_ironic_node(self,port_list,driver_info,properties):

        ironic_node_name                  = self.bms_node_name
        port_group_name                   = ironic_node_name + "_pg"
        if not self.ironic_node_id:
           self.read()

        if self.ironic_node_obj:
           self.logger.info("Ironic node: %s already present, not creating it"%self.bms_node_name)
           self.logger.info("node-id:%s"%self.ironic_node_obj.uuid)
           return
        else:
           self.logger.info("Creating Ironic node: %s "%self.bms_node_name)
           self.ironic_h.obj.node.create(name=ironic_node_name,driver='pxe_ipmitool',\
                                        driver_info=driver_info,properties=properties)
           self.read() # to know self.ironic_node_obj.uuid used for port create

        self.portgroup_uuid = None
        if len(port_list) > 1:
           pg_obj = self.create_ironic_portgroup(self.ironic_node_obj.uuid,port_group_name,\
                                           port_list[0]['mac_addr'])
           if pg_obj:
              self.portgroup_uuid = pg_obj.uuid
        for i,port in enumerate(port_list):
            port_dl = {}
            port_dl['switch_info'] = port['switch_info']
            port_dl['port_id']     = port['port_id']
            port_dl['switch_id']   = port['switch_id']                 
            self.create_ironic_port(port=port_dl,node_uuid=self.ironic_node_obj.uuid,\
                               mac_address=port['mac_addr'],
                               portgroup_uuid=self.portgroup_uuid,pxe_enabled=port['pxe_enabled'])

    def set_ironic_node_state(self,new_state):
        if not self.ironic_node_id:
           self.read()

        if new_state == "available":
           self.ironic_h.obj.node.set_provision_state(self.ironic_node_id,"manage")
           self.ironic_h.obj.node.set_provision_state(self.ironic_node_id,"provide")
       
    def create(self):
        (self.vm_username, self.vm_password) = self.orch.get_image_account(
            self.image_name)
        if self.vm_id:
            return self.read()
        self.vn_ids = [self.orch.get_vn_id(x) for x in self.vn_objs]
        self.vm_obj = self.orch.get_vm_if_present(self.vm_name,
                                                  project_id=self.project_id)
        self.vm_objs = self.orch.get_vm_list(name_pattern=self.vm_name,
                                             project_id=self.project_id)
        if self.vm_obj:
            self.vm_id = self.vm_obj.id
            with self.printlock:
                self.logger.debug('VM %s already present, not creating it'
                                  % (self.vm_name))
            self.set_image_details(self.vm_obj)
        else:
            if self.inputs.is_gui_based_config():
                self.webui.create_vm(self)
            else:
                objs = self.orch.create_vm(
                    project_uuid=self.project_id,
                    image_name=self.image_name,
                    flavor=self.flavor,
                    vm_name=self.vm_name,
                    vn_objs=self.vn_objs,
                    node_name=self.node_name,
                    zone=self.zone,
                    sg_ids=self.sg_ids,
                    count=self.count,
                    userdata=self.userdata,
                    port_ids=self.port_ids,
                    fixed_ips=self.fixed_ips)
                self.created = True
                self.vm_obj = objs[0]
                self.vm_objs = objs
                self.vm_id = self.vm_objs[0].id

    # end setUp

    def verify_on_setup(self, force=False,refresh=False):
        #TO DO: sandipd - Need adjustments in multiple places to make verification success
        # in vcenter gateway setup.Will do gradually.For now made changes just needed to make few functionality
        #test cases pass
        if isinstance(self.orch,VcenterGatewayOrch):
            self.logger.debug('Skipping VM %s verification for vcenter gateway setup' % (self.vm_name))
            return True
        if not (self.inputs.verify_on_setup or force):
            self.logger.debug('Skipping VM %s verification' % (self.vm_name))
            return True
        result = True
        self.refresh = refresh
        vm_status = self.orch.wait_till_vm_is_active(self.vm_obj)
        if type(vm_status) is tuple:
            if vm_status[1] in 'ERROR':
                self.logger.warn("VM in error state. Asserting...")
                return False
            if vm_status[1] != 'ACTIVE':
                return False
        elif not vm_status:
            return False

        # BMS_LCM
        self.logger.debug('Skipping VM %s verification' % (self.vm_name))
        return True

    def cleanUp(self):
        self.delete()
        super(BmsLcmVMFixture, self).cleanUp()

    def delete(self, verify=False):
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if not self.created:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            if len(self.port_ids) != 0:
                for each_port_id in self.port_ids:
                    #in case of vcenter vm_obj dont't have option to  detach interface
                    if self.inputs.orchestrator == 'vcenter':
                        break
                    self.interface_detach(each_port_id)
            for vm_obj in list(self.vm_objs):
                for sec_grp in self.sg_ids:
                    self.logger.info("Removing the security group"
                                     " from VM %s" % (vm_obj.name))
                    self.remove_security_group(sec_grp)
                self.logger.info("Deleting VM %s" % (vm_obj.name))
                if self.inputs.is_gui_based_config():
                    self.webui.delete_vm(self)
                else:
                    self.orch.delete_vm(vm_obj)
                    self.vm_objs.remove(vm_obj)
            self.verify_cleared_from_setup(verify=verify)
        else:
            self.logger.info('Skipping the deletion of VM %s' %
                             (self.vm_name))
    # end cleanUp

    def verify_cleared_from_setup(self, check_orch=True, verify=False):
        # Not expected to do verification when self.count is > 1, right now
        if self.verify_is_run or verify:
             assert self.verify_vm_not_in_api_server(), ('VM %s is not removed '
                'from API Server' %(self.vm_name))
             if check_orch:
                 assert self.verify_vm_not_in_orchestrator(), ('VM %s is still'
                    'seen in orchestrator' % (self.vm_name))
             assert self.verify_vm_not_in_agent(), ('VM %s is still seen in '
                'one or more agents' % (self.vm_name))
             assert self.verify_vm_not_in_control_nodes(), ('VM %s is still '
                'seen in Control nodes' % (self.vm_name))

             assert self.verify_vm_flows_removed(), ('One or more flows of VM'
                ' %s is still seen in Compute node %s' %(self.vm_name,
                                                         self.vm_node_ip))
             for vn_fq_name in self.vn_fq_names:
                 try:
                     self.analytics_obj.verify_vm_not_in_opserver(
                         self.vm_id,
                         self.get_host_of_vm(),
                         vn_fq_name)
                 except PermissionDenied:
                     if not self.admin_connections:
                         raise
                     admin_analytics_obj = self.admin_connections.analytics_obj
                     admin_analytics_obj.verify_vm_not_in_opserver(
                         self.vm_id,
                         self.get_host_of_vm(),
                         vn_fq_name)
             # Trying a workaround for Bug 452
        # end if
        return True

    def wait_till_vm_is_up(self,refresh=False):
        self.logger.info('Waiting for VM %s to be up..' %(self.vm_name))
        self.refresh = refresh
        status = self.wait_till_vm_up()
        if not status:
            self.logger.error('VM %s does not seem to be fully up. Check logs'
                %(self.vm_name))
        return_status = None
        if type(status) == tuple:
            return_status = status[0]
        elif type(status) == bool:
            return_status = status

        # Get the console output in case of failures
        if not return_status:
            self.logger.debug(self.get_console_output())
        return return_status

    def wait_till_vm_is_active(self):
        status = self.orch.wait_till_vm_is_active(self.vm_obj)
        if type(status) == tuple:
            if status[1] in 'ERROR':
                return False
            elif status[1] in 'ACTIVE':
                return True
        elif type(status) == bool:
            return status

    @retry(delay=5, tries=10)
    def wait_till_vm_up(self):
        vm_status = self.orch.wait_till_vm_is_active(self.vm_obj)
        if type(vm_status) == tuple:
            if vm_status[1] in 'ERROR':
                self.logger.warn("VM in error state. Asserting...")
                return (False, 'final')
#            assert False

            if vm_status[1] != 'ACTIVE':
                result = result and False
                return result
        elif type(vm_status) == bool and not vm_status:
            return (vm_status, 'final')

        result = self.verify_vm_launched()
        #console_check = self.nova_h.wait_till_vm_is_up(self.vm_obj)
        #result = result and self.nova_h.wait_till_vm_is_up(self.vm_obj)
        # if not console_check :
        #    import pdb; pdb.set_trace()
        #    self.logger.warn('Console logs didnt give enough info on bootup')
        self.vm_obj.get()
        result = result and self._gather_details()
        for vn_fq_name in self.vn_fq_names:
            if self.vnc_lib_fixture.get_active_forwarding_mode(vn_fq_name) != 'l2':
                if not result:
                    break
                ssh_wait_result = self.wait_for_ssh_on_vm()
                if not ssh_wait_result:
                    self.logger.debug('VM %s is NOT ready for SSH connections' % (
                        self.vm_name))
                result = result and ssh_wait_result
        if not result:
            self.logger.debug('VM %s does not seem to be fully up' % (
                              self.vm_name))
            self.logger.debug('Console output: %s' % self.get_console_output())
            return result
        return True
    # end wait_till_vm_up

