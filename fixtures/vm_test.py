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

from collections import defaultdict
from tcutils.pkgs.install import PkgHost, build_and_install
from security_group import get_secgrp_id_from_name, list_sg_rules
from tcutils.tcpdump_utils import start_tcpdump_for_intf,\
     stop_tcpdump_for_intf

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

    def __init__(self, connections, vm_name=None, vn_obj=None,
                 vn_objs=[], project_name=None,
                 image_name='ubuntu', subnets=[],
                 flavor=None,
                 node_name=None, sg_ids=[], count=1, userdata=None,
                 port_ids=[], fixed_ips=[], zone=None, vn_ids=[], uuid=None):
        self.connections = connections
        self.inputs = self.connections.inputs
        self.logger = self.connections.logger
        self.api_s_inspects = self.connections.api_server_inspects
        self.api_s_inspect = self.connections.api_server_inspect
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.ops_inspect = self.connections.ops_inspects
        self.orch = self.connections.orch
        self.quantum_h = self.connections.quantum_h
        self.vnc_lib_h = self.connections.get_vnc_lib_h()
        self.nova_h = self.connections.nova_h
        self.node_name = node_name
        self.zone = zone
        self.sg_ids = sg_ids
        self.count = count
        self.port_ids = port_ids
        self.fixed_ips = fixed_ips
        self.subnets = subnets
        if os.environ.has_key('ci_image'):
            image_name = os.environ.get('ci_image')
        self.image_name = image_name
        self.flavor = flavor
        self.project_name = project_name or self.inputs.stack_tenant
        self.vm_name = vm_name or get_random_name(self.project_name)
        self.vm_id = uuid
        self.vm_obj = None
        self.vm_ips = list()
        self.vn_objs = list((vn_obj and [vn_obj]) or vn_objs or
                            [self.orch.get_vn_obj_from_id(x) for x in vn_ids])
        if os.environ.has_key('ci_image'):
            cidrs = []
            for vn_obj in self.vn_objs:
                if vn_obj['network'].has_key('contrail:subnet_ipam'):
                    cidrs.extend(list(map(lambda obj: obj['subnet_cidr'],
                                          vn_obj['network']['contrail:subnet_ipam'])))
            if get_af_from_cidrs(cidrs) != 'v4':
                raise v4OnlyTestException('Disabling v6 tests for CI')
        self.vn_names = [self.orch.get_vn_name(x) for x in self.vn_objs]
        self.vn_fq_names = [':'.join(self.vnc_lib_h.id_to_fq_name(self.orch.get_vn_id(x)))
                            for x in self.vn_objs]
        self.vn_ids = vn_ids
        if len(self.vn_objs) == 1:
            self.vn_name = self.vn_names[0]
            self.vn_fq_name = self.vn_fq_names[0]
        self.already_present = False
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

    # end __init__

    def read(self):
        if self.vm_id:
            self.vm_obj = self.orch.get_vm_by_id(vm_id=self.vm_id)
            if not self.vm_obj:
                raise Exception('VM with id %s not found'%self.vm_id)
            self.vm_objs = [self.vm_obj]
            self.vm_name = self.vm_obj.name
            self.vn_names = self.orch.get_networks_of_vm(self.vm_obj)
            self.vn_objs = [self.orch.get_vn_obj_if_present(x)
                            for x in self.vn_names]
            self.vn_ids = [self.orch.get_vn_id(x) for x in self.vn_objs]
            self.vn_fq_names = [':'.join(self.vnc_lib_h.id_to_fq_name(x))
                                for x in self.vn_ids]
            self.vn_name = self.vn_names[0]
            self.vn_fq_name = self.vn_fq_names[0]
            self.vm_ip_dict = self.get_vm_ip_dict()
            self.vm_ips = self.get_vm_ips()

    def setUp(self):
        super(VMFixture, self).setUp()
        self.create()

    def create(self):
        if self.vm_id:
            return self.read()
        self.project_fixture = self.useFixture(
                ProjectFixture(vnc_lib_h=self.vnc_lib_h,
                               project_name=self.project_name,
                               connections=self.connections))
        self.vn_ids = [self.orch.get_vn_id(x) for x in self.vn_objs]
        self.vm_obj = self.orch.get_vm_if_present(self.vm_name,
                           project_id=self.project_fixture.uuid)
        self.vm_objs = self.orch.get_vm_list(name_pattern=self.vm_name,
                           project_id=self.project_fixture.uuid)
        if self.vm_obj:
            self.vm_id = self.vm_obj.id
            self.already_present = True
            with self.printlock:
                self.logger.debug('VM %s already present, not creating it'
                                  % (self.vm_name))
        else:
            if self.inputs.is_gui_based_config():
                self.webui.create_vm(self)
            else:
                objs = self.orch.create_vm(
                    project_uuid=self.project_fixture.uuid,
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
#                time.sleep(5)
                self.vm_obj = objs[0]
                self.vm_objs = objs
                self.vm_id = self.vm_objs[0].id
                self.vm_obj.get()
                self.zone = getattr(self.vm_obj,'OS-EXT-AZ:availability_zone', None)
                self.image_name = self.orch.get_image_name_for_zone(
                                        image_name=self.image_name,
                                        zone=self.zone)
        (self.vm_username, self.vm_password) = self.orch.get_image_account(
            self.image_name)

    # end setUp

    def get_uuid(self):
        return self.vm_id

    def get_fq_name(self):
        return self.vm_name

    def get_name(self):
        return self.vm_name

    def get_vm_ips(self, vn_fq_name=None, af=None):
        if not af:
           af = self.inputs.get_af()
        af = ['v4', 'v6'] if 'dual' in af else af
        if vn_fq_name:
            vm_ips = self.get_vm_ip_dict()[vn_fq_name]
        else:
            if not getattr(self, 'vm_ips', None):
                for vm_obj in self.vm_objs:
                    for vn_name in self.vn_names:
                        for ip in self.orch.get_vm_ip(vm_obj, vn_name):
                            if self.hack_for_v6(ip):
                                continue
                            self.vm_ips.append(ip)
            vm_ips = self.vm_ips
        return [ip for ip in vm_ips if get_af_type(ip) in af]

    def hack_for_v6(self, ip):
        if 'v6' in self.inputs.get_af() and not is_v6(ip):
            return True
        return False

    @property
    def vm_ip(self):
        return self.vm_ips[0] if self.vm_ips else None

    def verify_vm_launched(self):
        self.vm_launch_flag = True
        for vm_obj in self.vm_objs:
            if not self.orch.get_vm_detail(vm_obj):
                self.logger.error('VM %s is not launched yet' %vm_obj.id)
                self.vm_launch_flag = False
                return False
            self.logger.info("VM %s ID is %s" % (vm_obj.name, vm_obj.id))
            self.logger.info('VM %s launched on Node %s'
                             % (vm_obj.name, self.get_host_of_vm(vm_obj)))
        self.vm_ips = self.get_vm_ips()
        if not self.vm_ips:
            self.logger.error('VM didnt seem to have got any IP')
            self.vm_launch_flag = False
            return False
        self.vm_launch_flag = True
        return True
    # end verify_vm_launched

    @property
    def vm_node_ip(self):
        if not getattr(self, '_vm_node_ip', None):
            self._vm_node_ip = self.inputs.get_host_ip(self.get_host_of_vm())
        return self._vm_node_ip

    def get_host_of_vm(self, vm_obj=None):
        vm_obj = vm_obj or self.vm_obj
        attr = '_host_'+vm_obj.name
        if not getattr(self, attr, None):
            setattr(self, attr, self.orch.get_host_of_vm(vm_obj))
        return getattr(self, attr, None)

    @property
    def vm_node_data_ip(self):
        if not getattr(self, '_vm_data_node_ip', None):
            self._vm_node_data_ip = self.inputs.get_host_data_ip(self.get_host_of_vm())
        return self._vm_node_data_ip

    def get_compute_host(self):
        return self.vm_node_data_ip

    def set_vm_creds(self, username, password):
        self.vm_username = username
        self.vm_password = password

    def get_vm_username(self):
        return self.vm_username

    def get_vm_password(self):
        return self.vm_password

    @retry(delay=1, tries=5)
    def get_vm_obj_from_api_server(self, cfgm_ip=None, refresh=False):
        cfgm_ip = cfgm_ip or self.inputs.cfgm_ip
        if not getattr(self, 'cs_vm_obj', None):
            self.cs_vm_obj = dict()
        if not self.cs_vm_obj.get(cfgm_ip) or refresh:
            vm_obj = self.api_s_inspects[cfgm_ip].get_cs_vm(self.vm_id, refresh)
            self.cs_vm_obj[cfgm_ip] = vm_obj
        ret = True if self.cs_vm_obj[cfgm_ip] else False
        return (ret, self.cs_vm_obj[cfgm_ip])

    def get_vm_objs(self):
        for cfgm_ip in self.inputs.cfgm_ips:
            vm_obj = self.get_vm_obj_from_api_server(cfgm_ip)[1]
            if not vm_obj:
                return None
        return self.cs_vm_obj

    @retry(delay=1, tries=5)
    def get_vmi_obj_from_api_server(self, cfgm_ip=None, refresh=False):
        cfgm_ip = cfgm_ip or self.inputs.cfgm_ip
        if not getattr(self, 'cs_vmi_objs', None):
            self.cs_vmi_objs = dict()
        if not self.cs_vmi_objs.get(cfgm_ip) or refresh:
            vmi_obj = self.api_s_inspects[cfgm_ip].get_cs_vmi_of_vm(
                      self.vm_id, refresh)
            self.cs_vmi_objs[cfgm_ip] = vmi_obj
        ret = True if self.cs_vmi_objs[cfgm_ip] else False
        return (ret, self.cs_vmi_objs[cfgm_ip])

    def get_vmi_objs(self, refresh=False):
        for cfgm_ip in self.inputs.cfgm_ips:
            vmi_obj = self.get_vmi_obj_from_api_server(cfgm_ip, refresh)[1]
            if not vmi_obj:
                return None
        return self.cs_vmi_objs

    @retry(delay=1, tries=5)
    def get_iip_obj_from_api_server(self, cfgm_ip=None, refresh=False):
        cfgm_ip = cfgm_ip or self.inputs.cfgm_ip
        if not getattr(self, 'cs_instance_ip_objs', None):
            self.cs_instance_ip_objs = dict()
        if not self.cs_instance_ip_objs.get(cfgm_ip) or refresh:
            iip_obj = self.api_s_inspects[cfgm_ip].get_cs_instance_ips_of_vm(
                      self.vm_id, refresh)
            self.cs_instance_ip_objs[cfgm_ip] = iip_obj
        ret = True if self.cs_instance_ip_objs[cfgm_ip] else False
        return (ret, self.cs_instance_ip_objs[cfgm_ip])

    def get_iip_objs(self, refresh=False):
        for cfgm_ip in self.inputs.cfgm_ips:
            iip_obj = self.get_iip_obj_from_api_server(cfgm_ip, refresh)[1]
            if not iip_obj:
                return None
        return self.cs_instance_ip_objs

    def get_vm_ip_dict(self):
        if not getattr(self, 'vm_ip_dict', None):
            self.vm_ip_dict = defaultdict(list)
            iip_objs = self.get_iip_obj_from_api_server()[1]
            for iip_obj in iip_objs:
                ip = iip_obj.ip
                if self.hack_for_v6(ip):
                    continue
                self.vm_ip_dict[iip_obj.vn_fq_name].append(ip)
        return self.vm_ip_dict

    def add_security_group(self, secgrp):
        self.orch.add_security_group(vm_id=self.vm_obj.id, sg_id=secgrp)

    def remove_security_group(self, secgrp):
        self.orch.remove_security_group(vm_id=self.vm_obj.id, sg_id=secgrp)

    def verify_security_group(self, secgrp):

        result = False
        errmsg = "Security group %s is not attached to the VM %s" % (secgrp,
                                                                     self.vm_name)
        cs_vmi_objs = self.get_vmi_obj_from_api_server(refresh=True)[1]
        for cs_vmi_obj in cs_vmi_objs:
            vmi = cs_vmi_obj['virtual-machine-interface']
            if vmi.has_key('security_group_refs'):
                sec_grps = vmi['security_group_refs']
                for sec_grp in sec_grps:
                    if secgrp == sec_grp['to'][-1]:
                        self.logger.info(
                            "Security group %s is attached \
        				to the VM %s", secgrp, self.vm_name)
                        result = True

        if not result:
            self.logger.warn(errmsg)
            return result, errmsg

        result, msg = self.verify_sec_grp_in_agent(secgrp)
        if not result:
            self.logger.warn(msg)
            return result, msg

        result, msg = self.verify_sg_acls_in_agent(secgrp)
        if not result:
            self.logger.warn(msg)
            return result, msg

        return result, None

    @retry(delay=2, tries=4)
    def verify_sec_grp_in_agent(self, secgrp, domain='default-domain'):
        # this method verifies sg secgrp attached to vm info in agent
        secgrp_fq_name = ':'.join([domain,
                                   self.project_name,
                                   secgrp])

        sg_id = get_secgrp_id_from_name(
            self.connections,
            secgrp_fq_name)

        inspect_h = self.agent_inspect[self.vm_node_ip]
        sg_info = inspect_h.get_sg(sg_id)
        if sg_info:
            self.logger.info("Agent: Security group %s is attached to the VM %s",
                             secgrp, self.vm_name)
            return True, None

        errmsg = "Agent: Security group %s is NOT attached to the VM %s" % (secgrp,
                                                                            self.vm_name)
        return False, errmsg

    @retry(delay=2, tries=4)
    def verify_sg_acls_in_agent(self, secgrp, domain='default-domain'):
        secgrp_fq_name = ':'.join([domain,
                                   self.project_name,
                                   secgrp])

        sg_id = get_secgrp_id_from_name(
            self.connections,
            secgrp_fq_name)

        rules = self.orch.get_security_group_rules(sg_id)
        inspect_h = self.agent_inspect[self.vm_node_ip]
        acls_list = inspect_h.get_sg_acls_list(sg_id)

        errmsg = "sg acl rule not found in agent"
        result = False
        for rule in rules:
            result = False
            uuid = rule.get('id', None)
            if not uuid:
                uuid = rule['rule_uuid']
            for acl in acls_list:
                for r in acl['entries']:
                    if r.has_key('uuid'):
                        if r['uuid'] == uuid:
                            result = True
                            break
                if result:
                    break
            if not result:
                return result, errmsg

        return True, None

    def verify_on_setup(self, force=False):
        if not (self.inputs.verify_on_setup or force):
            self.logger.info('Skipping VM %s verification' % (self.vm_name))
            return True
        result = True
        vm_status = self.orch.wait_till_vm_is_active(self.vm_obj)
        if type(vm_status) is tuple:
            if vm_status[1] in 'ERROR':
                self.logger.warn("VM in error state. Asserting...")
                return False
            if vm_status[1] != 'ACTIVE':
                return False
        elif not vm_status:
            return False

        self.verify_vm_launched()
        if len(self.vm_ips) < 1:
            return False

        self.verify_vm_flag = True
        if self.inputs.verify_thru_gui():
            self.webui.verify_vm(self)
        result = self.verify_vm_in_api_server()
        if not result:
            self.logger.error('VM %s verification in API Server failed'
                              % (self.vm_name))
            return result
        result = self.verify_vm_in_agent()
        if not result:
            self.logger.error('VM %s verification in Agent failed'
                              % (self.vm_name))
            return result
        result = self.verify_vm_in_control_nodes()
        if not result:
            self.logger.error('Route verification for VM %s in Controlnodes'
                              ' failed ' % (self.vm_name))
            return result
        result = self.verify_vm_in_opserver()
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
            cs_vmi_objs_vm = self.get_vmi_obj_from_api_server()[1]
            inspect_h = self.agent_inspect[self.vm_node_ip]
            for vmi_obj in cs_vmi_objs_vm:
                tap_intf = {}
                tmp_vmi_id = vmi_obj.uuid
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
            cs_vmi_objs_vm = self.get_vmi_obj_from_api_server()[1]
            inspect_h = self.agent_inspect[self.vm_node_ip]
            for vmi_obj in cs_vmi_objs_vm:
                tap_intf = {}
                tmp_vmi_id = vmi_obj.uuid
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

        self.get_vm_objs()
        self.get_vmi_objs()
        self.get_iip_objs()

        for cfgm_ip in self.inputs.cfgm_ips:
            self.logger.info("Verifying in api server %s" % (cfgm_ip))
            if not self.cs_instance_ip_objs[cfgm_ip]:
                with self.printlock:
                    self.logger.error('Instance IP of VM ID %s not seen in '
                                      'API Server ' % (self.vm_id))
                self.vm_in_api_flag = self.vm_in_api_flag and False
                return False

        for ips in self.get_vm_ip_dict().values():
            if set(ips) | set(self.vm_ips) != set(self.vm_ips):
                with self.printlock:
                    self.logger.warn('Instance IP %s from API Server is '
                                     ' not found in VM IP list %s' % (ip, str(self.vm_ips)))
                self.vm_in_api_flag = self.vm_in_api_flag and False
                return False
        for vmi_obj in self.cs_vmi_objs[self.inputs.cfgm_ip]:
            vmi_vn_id = vmi_obj.vn_uuid
            vmi_vn_fq_name = vmi_obj.vn_fq_name
            # ToDo: msenthil the checks have to be other way around
            if vmi_vn_id not in self.vn_ids:
                with self.printlock:
                    self.logger.warn('VMI %s of VM %s is not mapped to the '
                                     'right VN ID in API Server' % (vmi_vn_id, self.vm_name))
                self.vm_in_api_flag = self.vm_in_api_flag and False
                return False
            self.cs_vmi_obj[vmi_vn_fq_name] = vmi_obj
        with self.printlock:
            self.logger.info("API Server validations for VM %s passed in api server %s"
                             % (self.vm_name, self.inputs.cfgm_ip))
        self.vm_in_api_flag = self.vm_in_api_flag and True
        return True
    # end verify_vm_in_api_server

    @retry(delay=2, tries=25)
    def verify_vm_not_in_api_server(self):

        self.verify_vm_not_in_api_server_flag = True
        for ip in self.inputs.cfgm_ips:
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
            if api_inspect.get_cs_vmi_of_vm(self.vm_id,
                    refresh=True) is not None:
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

    def get_tap_intf_of_vmi(self, vmi_uuid):
        inspect_h = self.agent_inspect[self.vm_node_ip]
        vna_tap_id = inspect_h.get_vna_tap_interface_by_vmi(vmi_id=vmi_uuid)
        return vna_tap_id[0]

    def get_tap_intf_of_vm(self):
        inspect_h = self.agent_inspect[self.vm_node_ip]
        tap_intfs = inspect_h.get_vna_tap_interface_by_vm(vm_id=self.vm_id)
        return tap_intfs

    def get_vmi_ids(self):
        if not getattr(self, 'vmi_ids', None):
            self.vmi_ids = dict()
            vmi_objs = self.get_vmi_obj_from_api_server()[1]
            for vmi_obj in vmi_objs:
                self.vmi_ids[vmi_obj.vn_fq_name] = vmi_obj.uuid
        return self.vmi_ids

    def get_mac_addr_from_config(self):
        if not getattr(self, 'mac_addr', None):
            vmi_objs = self.get_vmi_obj_from_api_server()[1]
            for vmi_obj in vmi_objs:
                self.mac_addr[vmi_obj.vn_fq_name] = vmi_obj.mac_addr
        return self.mac_addr

    def get_agent_label(self):
        if not getattr(self, 'agent_label', None):
            for (vn_fq_name, vmi) in self.get_vmi_ids().iteritems():
                self.agent_label[vn_fq_name] = self.get_tap_intf_of_vmi(vmi)['label']
        return self.agent_label

    def get_local_ips(self):
        if not getattr(self, 'local_ips', None):
            for (vn_fq_name, vmi) in self.get_vmi_ids().iteritems():
                self.local_ips[vn_fq_name] = self.get_tap_intf_of_vmi(vmi)['mdata_ip_addr']
        return self.local_ips

    def get_local_ip(self):
        if not getattr(self, '_local_ip', None):
            local_ips = self.get_local_ips()
            if len(self.vn_fq_names) > 1:
                for vn_fq_name in self.vn_fq_names:
                    if local_ips[vn_fq_name] != '0.0.0.0':
                        if self.ping_vm_from_host(vn_fq_name):
                            self._local_ip = self.local_ips[vn_fq_name]
                            break
            else:
                self._local_ip = local_ips and local_ips.values()[0]
        return getattr(self, '_local_ip', '')

    @property
    def local_ip(self):
        return self.get_local_ip()

    @retry(delay=2, tries=20)
    def verify_vm_in_agent(self):
        ''' Verifies whether VM has got created properly in agent.

        '''
        self.vm_in_agent_flag = True

        #Verification in vcenter plugin introspect
        if getattr(self.orch,'verify_vm_in_vcenter',None):
            assert self.orch.verify_vm_in_vcenter(self.vm_obj)

        inspect_h = self.agent_inspect[self.vm_node_ip]
        for vn_fq_name in self.vn_fq_names:
            (domain, project, vn) = vn_fq_name.split(':')
            agent_vn_obj = inspect_h.get_vna_vn(domain, project, vn)
            if not agent_vn_obj:
                self.logger.warn('VN %s is not seen in agent %s'
                                 % (vn_fq_name, self.vm_node_ip))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False

            # Check if the VN ID matches between the Orchestration S and Agent
            # ToDo: msenthil should be == check of vn_id[vn_fq_name] rather
            # than list match
            if agent_vn_obj['uuid'] not in self.vn_ids:
                self.logger.warn('Unexpected VN UUID %s found in agent %s '
                                 'Expected: One of %s' % (agent_vn_obj['uuid'],
                                 self.vm_node_ip, self.vn_ids))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False
            try:
                vna_tap_id = self.get_tap_intf_of_vmi(self.get_vmi_ids()[vn_fq_name])
            except Exception as e:
                vna_tap_id = None

            self.tap_intf[vn_fq_name] = vna_tap_id
            if not self.tap_intf[vn_fq_name]:
                self.logger.error('Tap interface in VN %s for VM %s not'
                                  'seen in agent %s '
                                  % (vn_fq_name, self.vm_name, self.vm_node_ip))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False
            mac_addr = self.tap_intf[vn_fq_name]['mac_addr']
            if mac_addr != self.get_mac_addr_from_config()[vn_fq_name]:
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

            self.logger.info("tap intf: %s" % (str(self.tap_intf[vn_fq_name])))

            self.agent_vrf_name[vn_fq_name] = self.tap_intf[
                vn_fq_name]['vrf_name']

            self.logger.info("agent vrf name: %s" %
                             (str(self.agent_vrf_name[vn_fq_name])))

            try:
                agent_vrf_objs = inspect_h.get_vna_vrf_objs(
                    domain, project, vn)
            except Exception as e:
                agent_vrf_objs = None

            self.logger.info("vrf obj : %s" % (str(agent_vrf_objs)))
            if not agent_vrf_objs:
                return False
            # Bug 1372858
            try:
                agent_vrf_obj = self.get_matching_vrf(
                    agent_vrf_objs['vrf_list'],
                    self.agent_vrf_name[vn_fq_name])
            except Exception as e:
                self.logger.warn("Exception: %s" % (e))
                return False

            self.agent_vrf_id[vn_fq_name] = agent_vrf_obj['ucindex']
            self.agent_path[vn_fq_name] = list()
            self.agent_label[vn_fq_name] = list()
            try:
                for vm_ip in self.vm_ip_dict[vn_fq_name]:
                    self.agent_path[vn_fq_name].append(
                        inspect_h.get_vna_active_route(
                            vrf_id=self.agent_vrf_id[vn_fq_name],
                            ip=vm_ip))
            except Exception as e:
                return False
            if not self.agent_path[vn_fq_name]:
                with self.printlock:
                    self.logger.warn('No path seen for VM IP %s in agent %s'
                                     % (self.vm_ip_dict[vn_fq_name], self.vm_node_ip))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False
            for agent_path in self.agent_path[vn_fq_name]:
                agent_label = agent_path['path_list'][0]['label']
                self.agent_label[vn_fq_name].append(agent_label)

                if agent_path['path_list'][0]['nh']['itf'] != \
                        self.tap_intf[vn_fq_name]['name']:
                    self.logger.warning("Active route in agent for %s is "
                                        "not pointing to right tap interface. It is %s "
                                        % (self.vm_ip_dict[vn_fq_name],
                                           agent_path['path_list'][0]['nh']['itf']))
                    self.vm_in_agent_flag = self.vm_in_agent_flag and False
                    return False
                else:
                    self.logger.debug('Active route in agent is present for'
                                      ' VMI %s ' % (self.tap_intf[vn_fq_name]['name']))

                if self.tap_intf[vn_fq_name]['label'] != agent_label:
                    self.logger.warning('VM %s label mismatch! ,'
                                        ' Expected : %s , Got : %s' % (self.vm_name,
                                                                       self.tap_intf[vn_fq_name]['label'], agent_label))
                    self.vm_in_agent_flag = self.vm_in_agent_flag and False
                    return False
                else:
                    self.logger.debug('VM %s labels in tap-interface and '
                                      'the route do match' % (self.vm_name))

            # Check if tap interface is set to Active
            if self.tap_intf[vn_fq_name]['active'] != 'Active':
                self.logger.warn('VM %s : Tap interface %s is not set to '
                                 'Active, it is : %s ' % (self.vm_name,
                                                          self.tap_intf[
                                                              vn_fq_name]['name'],
                                                          self.tap_intf[vn_fq_name]['active']))
            else:
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
                    mac=mac_addr)
            except Exception as e:
                self.agent_l2_path[vn_fq_name] = None
            if not self.agent_l2_path[vn_fq_name]:
                with self.printlock:
                    self.logger.warning('No Layer 2 path is seen for VM MAC '
                                        '%s in agent %s' % (mac_addr,
                                                            self.vm_node_ip))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False
            else:
                with self.printlock:
                    self.logger.info('Layer 2 path is seen for VM MAC %s '
                                     'in agent %s' % (mac_addr,
                                                      self.vm_node_ip))
            self.agent_l2_label[vn_fq_name] = self.agent_l2_path[
                vn_fq_name]['routes'][0]['path_list'][0]['label']
            self.agent_vxlan_id[vn_fq_name] = self.agent_l2_path[
                vn_fq_name]['routes'][0]['path_list'][0]['vxlan_id']

            # Check if Tap interface of VM is present in the Agent layer
            # route table
            if self.agent_l2_path[vn_fq_name]['routes'][0]['path_list'][0][
                    'nh']['itf'] != self.tap_intf[vn_fq_name]['name']:
                with self.printlock:
                    self.logger.warn("Active layer 2 route in agent for %s "
                                     "is not pointing to right tap interface."
                                     " It is %s "
                                     % (self.vm_ip_dict[vn_fq_name],
                                        self.agent_l2_path[vn_fq_name][
                                         'routes'][0]['path_list'][0]['nh']['itf']))
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False
            else:
                with self.printlock:
                    self.logger.info(
                        'Active layer 2 route in agent is present for VMI %s ' %
                        (self.tap_intf[vn_fq_name]['name']))
            if self.agent_l2_path[vn_fq_name]['routes'][0]['path_list'][0]['active_tunnel_type'] == 'VXLAN':
                if self.agent_vxlan_id[vn_fq_name] != \
                        self.tap_intf[vn_fq_name]['vxlan_id']:
                    with self.printlock:
                        self.logger.warn("vxlan_id  mismatch between interface "
                                         "introspect %s and l2 route table %s"
                                         % (self.tap_intf[vn_fq_name]['vxlan_id'],
                                            self.agent_vxlan_id[vn_fq_name]))
                    self.vm_in_agent_flag = self.vm_in_agent_flag and False
                    return False

                else:
                    with self.printlock:
                        self.logger.info('vxlan_id (%s) matches bw route table'
                                         ' and interface table'
                                         % self.agent_vxlan_id[vn_fq_name])

            else:

                if self.agent_l2_label[vn_fq_name] !=\
                        self.tap_intf[vn_fq_name]['l2_label']:
                    with self.printlock:
                        self.logger.warn("L2 label mismatch between interface "
                                         "introspect %s and l2 route table %s"
                                         % (self.tap_intf[vn_fq_name]['l2_label'],
                                            self.agent_l2_label[vn_fq_name]))
                    self.vm_in_agent_flag = self.vm_in_agent_flag and False
                    return False
                else:
                    with self.printlock:
                        self.logger.info('L2 label(%s) matches bw route table'

                                         ' and interface table'
                                         % self.agent_l2_label[vn_fq_name])

            # api_s_vn_obj = self.api_s_inspect.get_cs_vn(
            # project=vn_fq_name.split(':')[1], vn=vn_fq_name.split(':')[2], refresh=True)
            # if api_s_vn_obj['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['enable_dhcp']:
            #   if (self.agent_l2_path[vn_fq_name]['routes'][0]['path_list'][0]['flood_dhcp']) != 'false':
            #          with self.printlock:
            #            self.logger.warn("flood_dhcp flag is set to True \
            #                             for mac %s "
            #                             %(self.agent_l2_path[vn_fq_name]['mac']) )
            #          self.vm_in_agent_flag = self.vm_in_agent_flag and False
            #          return False
            # else:
            #   if (self.agent_l2_path[vn_fq_name]['routes'][0]['path_list'][0]['flood_dhcp']) != 'true':
            #          with self.printlock:
            #            self.logger.warn("flood_dhcp flag is set to False \
            #                             for mac %s "
            #                             %(self.agent_l2_path[vn_fq_name]['mac']) )
            #          self.vm_in_agent_flag = self.vm_in_agent_flag and False
            #          return False

            # L2 verification end here
            # Check if VN for the VM and route for the VM is present on all
            # compute nodes
            if not self.verify_in_all_agents(vn_fq_name):
                self.vm_in_agent_flag = self.vm_in_agent_flag and False
                return False

        # end for vn_fq_name in self.vn_fq_names

        # Ping to VM IP from host
        if '169.254' not in self.local_ip:
            with self.printlock:
                self.logger.error('Ping to one of the 169.254.x.x IPs of the VM'
                                  ' should have passed. It failed! ')
            self.vm_in_agent_flag = self.vm_in_agent_flag and False
            return False
        with self.printlock:
            self.logger.info("VM %s Verifications in Agent is fine" %
                             (self.vm_name))
        self.vm_in_agent_flag = self.vm_in_agent_flag and True
        return True
    # end verify_vm_in_agent

    def get_matching_vrf(self, vrf_objs, vrf_name):
        self.logger.info("vrf_objs: %s" % (str(vrf_objs)))
        self.logger.info("vrf_name: %s" % (str(vrf_name)))
        return [x for x in vrf_objs if x['name'] == vrf_name][0]

    def reset_state(self, state):
        self.vm_obj.reset_state(state)

    def ping_vm_from_host(self, vn_fq_name):
        ''' Ping the VM metadata IP from the host
        '''
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
        if len(self.inputs.compute_ips) > 10:
            self.logger.warn('Skipping verification on all agents since '
                             'there are more than 10 computes in the box, '
                             'until the subroutine supports gevent/mp')
            return True
        (domain, project, vn_name) = vn_fq_name.split(':')
        for compute_ip in self.inputs.compute_ips:
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
                agent_vrf_objs['vrf_list'],
                self.agent_vrf_name[vn_fq_name])
            agent_vrf_id = agent_vrf_obj['ucindex']
            for vm_ip in self.vm_ip_dict[vn_fq_name]:
                agent_path = inspect_h.get_vna_active_route(
                    vrf_id=agent_vrf_id, ip=vm_ip)
                agent_label = agent_path['path_list'][0]['label']
                if agent_label not in self.agent_label[vn_fq_name]:
                    self.logger.warn(
                        'The route for VM IP %s in Node %s is having '
                        'incorrect label. Expected: %s, Seen : %s' % (
                            vm_ip, compute_ip,
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
                vrf_id=agent_vrf_id,
                mac=self.get_mac_addr_from_config()[vn_fq_name])
            agent_l2_label = agent_l2_path[
                'routes'][0]['path_list'][0]['label']
            if agent_l2_label != self.agent_l2_label[vn_fq_name]:
                self.logger.warn('The route for VM MAC %s in Node %s '
                                 'is having incorrect label. Expected: %s, Seen: %s'
                                 % (self.mac_addr[vn_fq_name], compute_ip,
                                    self.agent_l2_label[vn_fq_name], agent_l2_label))
                return False
            self.logger.info(
                'Route for VM MAC %s is consistent in agent %s ' %
                (self.mac_addr[vn_fq_name], compute_ip))
        # end for
        return True
    # end verify_in_all_agents

    def ping_to_vn(self, dst_vm_fixture, vn_fq_name=None, af=None, *args, **kwargs):
        '''
        Ping all the ips belonging to a specific VN of a VM from another
        Optionally can specify the address family too (v4, v6 or dual)
        return False if any of the ping fails
        '''
        vm_ips = dst_vm_fixture.get_vm_ips(vn_fq_name=vn_fq_name, af=af)
        for ip in vm_ips:
            if not self.ping_to_ip(ip=ip, *args, **kwargs):
                return False
        return True

    def ping_to_ip(self, ip, return_output=False, other_opt='', size='56', count='5'):
        '''Ping from a VM to an IP specified.

        This method logs into the VM from the host machine using ssh and runs ping test to an IP.
        '''
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        fab_connections.clear()
        af = get_af_type(ip)
        try:
#            self.orch.put_key_file_to_host(self.vm_node_ip)
            with hide('everything'):
                with settings(host_string='%s@%s' % (host['username'],
                                                     self.vm_node_ip), password=host['password'],
                              warn_only=True, abort_on_prompts=False):
                    vm_host_string = '%s@%s' % (
                        self.vm_username, self.local_ip)
                    if af is None:
                        cmd = "python -c 'import socket; socket.getaddrinfo" +\
                            "(\"%s\"\, None\, socket.AF_INET6)'" % ip
                        output = run_fab_cmd_on_node(host_string=vm_host_string,
                                                     password=self.vm_password,
                                                     cmd=cmd)
                        util = 'ping' if output else 'ping6'
                    else:
                        util = 'ping6' if af == 'v6' else 'ping'
                    cmd = '%s -s %s -c %s %s %s' % (util,
                                                    str(size), str(count), other_opt, ip)
                    output = run_fab_cmd_on_node(host_string=vm_host_string,
                                                 password=self.vm_password,
                                                 cmd=cmd)
                    self.logger.debug(output)
            if return_output == True:
                return output
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying ping from VM')
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
            self.logger.warn("Got exception in ping_to_ip:%s" % (e))
            return False
    # end ping_to_ip

    def ping_to_ipv6(self, *args, **kwargs):
        '''Ping from a VM to an IPV6 specified.

        This method logs into the VM from the host machine using ssh and runs ping6 test to an IPV6.
        '''
        return self.ping_to_ip(*args, **kwargs)
    # end ping_to_ipv6

    @retry(delay=1, tries=10)
    def ping_with_certainty(self, ip=None, return_output=False, other_opt='',
                            size='56', count='5', expectation=True,
                            dst_vm_fixture=None, vn_fq_name=None, af=None):
        '''
        Better to call this instead of ping_to_ip.
        Set expectation to False if you want ping to fail
        Can be used for both ping pass and fail scenarios with retry
        '''
        if dst_vm_fixture:
            output = self.ping_to_vn(dst_vm_fixture=dst_vm_fixture,
                                     vn_fq_name=vn_fq_name, af=af,
                                     return_output=False, size=size,
                                     other_opt=other_opt, count=count)
        else:
            output = self.ping_to_ip(ip=ip, return_output=False,
                                     other_opt=other_opt, size=size,
                                     count=count)
        return (output == expectation)

    def verify_vm_not_in_orchestrator(self):
        if not self.orch.is_vm_deleted(self.vm_obj):
            with self.printlock:
                self.logger.warn("VM %s is still found in Compute(nova) "
                                 "server-list" % (self.vm_name))
            return False
        return True

    @retry(delay=2, tries=20)
    def verify_vm_not_in_agent(self):
        '''Verify that the VM is fully removed in all Agents.

        '''
        #Verification in vcenter plugin introspect
        if getattr(self.orch,'verify_vm_not_in_vcenter',None):
            assert self.orch.verify_vm_not_in_vcenter(self.vm_obj)

        result = True
        self.verify_vm_not_in_agent_flag = True
        self.vrfs = dict()
        self.vrfs = self.get_vrf_ids_accross_agents()
        inspect_h = self.agent_inspect[self.vm_node_ip]
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
            self.verify_vm_not_in_agent_flag = \
                self.verify_vm_not_in_agent_flag and False
            result = result and False
        for k, v in self.vrfs.items():
            inspect_h = self.agent_inspect[k]
            for vn_fq_name in self.vn_fq_names:
                if vn_fq_name in v:
                    for vm_ip in self.vm_ip_dict[vn_fq_name]:
                        if inspect_h.get_vna_active_route(
                                vrf_id=v[vn_fq_name],
                                ip=vm_ip) is not None:
                            self.logger.warn(
                                "Route for VM %s, IP %s is still seen in agent %s" %
                                (self.vm_name, vm_ip, self.vm_node_ip))
                            self.verify_vm_not_in_agent_flag = \
                                self.verify_vm_not_in_agent_flag and False
                            result = result and False
                else:
                    continue
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
                for vm_ip in self.vm_ip_dict[vn_fq_name]:
                    if inspect_h.get_vna_active_route(
                            vrf_id=self.agent_vrf_id[vn_fq_name],
                            ip=vm_ip) is not None:
                        self.logger.warn(
                            "Route for VM %s, IP %s is still seen in agent %s " %
                            (self.vm_name, vm_ip, compute_ip))
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
            self.logger.exception("Exception in get_control_nodes")
        finally:
            return bgp_ips

    def get_ctrl_nodes_in_rt_group(self):
        if getattr(self, 'bgp_ips', None):
            return self.bgp_ips
        rt_list = []
        peer_list = []
        for vn_fq_name in self.vn_fq_names:
            vn_name = vn_fq_name.split(':')[-1]
            ri_name = vn_fq_name + ':' + vn_name
            ri = self.vnc_lib_h.routing_instance_read(fq_name=[ri_name])
            rt_refs = ri.get_route_target_refs()
            for rt_ref in rt_refs:
                rt_obj = self.vnc_lib_h.route_target_read(id=rt_ref['uuid'])
                rt_list.append(rt_obj.name)
        for rt in rt_list:
            ctrl_node = self.get_active_controller()
            ctrl_node = self.inputs.get_host_ip(ctrl_node)
            peer_list.append(ctrl_node)
            rt_group_entry = self.cn_inspect[
                ctrl_node].get_cn_rtarget_group(rt)
            if rt_group_entry['peers_interested'] is not None:
                for peer in rt_group_entry['peers_interested']:
                    if peer in self.inputs.host_names:
                        peer = self.inputs.host_data[peer]['host_ip']
                        peer_list.append(peer)
                    else:
                        self.logger.info(
                            '%s is not defined as a control node in the topology' % peer)
        self.bgp_ips = list(set(peer_list))
        return self.bgp_ips
    # end get_ctrl_nodes_in_rt_group

    @retry(delay=5, tries=20)
    def verify_vm_in_control_nodes(self):
        ''' Validate routes are created in Control-nodes for this VM

        '''
        self.vm_in_cn_flag = True
        for vn_fq_name in self.vn_fq_names:
            for cn in self.get_ctrl_nodes_in_rt_group():
                vn_name = vn_fq_name.split(':')[-1]
                ri_name = vn_fq_name + ':' + vn_name
                # Check for VM route in each control-node
                for vm_ip in self.vm_ip_dict[vn_fq_name]:
                    cn_routes = self.cn_inspect[cn].get_cn_route_table_entry(
                        ri_name=ri_name, prefix=vm_ip)
                    if not cn_routes:
                        with self.printlock:
                            self.logger.warn(
                                'No route found for VM IP %s in Control-node %s' %
                                (vm_ip, cn))
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
                    if cn_routes[0]['label'] not in self.agent_label[vn_fq_name]:
                        with self.printlock:
                            self.logger.warn(
                                "Label for VM %s differs between Control-node "
                                "%s and Agent, Expected: %s, Seen: %s" %
                                (self.vm_name, cn, self.agent_label[vn_fq_name],
                                 cn_routes[0]['label']))
                            self.logger.debug(
                                'Route in CN %s : %s' % (cn, str(cn_routes)))
                        self.vm_in_cn_flag = self.vm_in_cn_flag and False
                        return False
        if self.verify_l2_routes_in_control_nodes() != True:
            with self.printlock:
                self.logger.warn("L2 verification for VM failed")
                return False
        self.vm_in_cn_flag = self.vm_in_cn_flag and True
        with self.printlock:
            self.logger.info("Verification in Control-nodes"
                             " for VM %s passed" % (self.vm_name))
        return True
    # end verify_vm_in_control_nodes

    def verify_l2_routes_in_control_nodes(self):
        for vn_fq_name in self.vn_fq_names:
            for cn in self.get_ctrl_nodes_in_rt_group():
                ri_name = vn_fq_name + ':' + vn_fq_name.split(':')[-1]
                self.logger.info('Starting all layer2 verification'
                                 ' in %s Control Node' % (cn))
                for vm_ip in self.vm_ip_dict[vn_fq_name]:
                    if is_v6(vm_ip):
                        self.logger.info('Skipping L2 verification of v6 '
                                         ' route on cn %s, not supported' % (cn))
                        continue
                    prefix = self.get_mac_addr_from_config()[vn_fq_name] + ',' + vm_ip
                    # Computing the ethernet tag for prefix here,
                    # format is  EncapTyepe-IP(0Always):0-VXLAN-MAC,IP
                    if vn_fq_name in self.agent_vxlan_id.keys():
                        ethernet_tag = "2-0:0" + '-' +\
                                       self.agent_vxlan_id[vn_fq_name]
                    else:
                        ethernet_tag = "2-0:0-0"
                    prefix = ethernet_tag + '-' + prefix
                    cn_l2_routes = self.cn_inspect[cn].get_cn_route_table_entry(
                        ri_name=ri_name,
                        prefix=prefix,
                        table='evpn.0')
                    if not cn_l2_routes:
                        self.logger.warn('No layer2 route found for VM MAC %s '
                                         'in CN %s: ri_name %s, prefix: %s' % (
                                             self.mac_addr[vn_fq_name], cn,
                                             ri_name, prefix))
                        self.vm_in_cn_flag = self.vm_in_cn_flag and False
                        return False
                    else:
                        self.logger.info('Layer2 route found for VM MAC %s in \
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
                        if cn_l2_routes[0]['label'] != \
                                self.agent_vxlan_id[vn_fq_name]:
                            with self.printlock:
                                self.logger.warn("L2 Label for VM %s differs "
                                                 " between Control-node %s and Agent, "
                                                 "Expected: %s, Seen: %s" % (self.vm_name,
                                                                             cn, self.agent_vxlan_id[
                                                                                 vn_fq_name],
                                                                             cn_l2_routes[0]['label']))
                                self.logger.debug('Route in CN %s : %s' % (cn,
                                                                           str(cn_l2_routes)))
                            self.vm_in_cn_flag = self.vm_in_cn_flag and False
                            return False
                        else:
                            with self.printlock:
                                self.logger.info("L2 Label for VM %s same "
                                                 "between Control-node %s and Agent, "
                                                 "Expected: %s, Seen: %s" %
                                                 (self.vm_name, cn,
                                                  self.agent_vxlan_id[
                                                      vn_fq_name],
                                                  cn_l2_routes[0]['label']))
                    else:
                        # Label in agent and control-node should match
                        if cn_l2_routes[0]['label'] != \
                                self.agent_l2_label[vn_fq_name]:
                            with self.printlock:
                                self.logger.warn("L2 Label for VM %s differs "
                                                 "between Control-node %s and Agent, "
                                                 "Expected: %s, Seen: %s" % (self.vm_name,
                                                                             cn, self.agent_l2_label[
                                                                                 vn_fq_name],
                                                                             cn_l2_routes[0]['label']))
                                self.logger.debug(
                                    'Route in CN %s: %s' % (cn, str(cn_l2_routes)))
                            self.vm_in_cn_flag = self.vm_in_cn_flag and False
                            return False
                        else:
                            with self.printlock:
                                self.logger.info("L2 Label for VM %s same "
                                                 "between Control-node %s and Agent, "
                                                 "Expected: %s, Seen: %s" %
                                                 (self.vm_name, cn,
                                                  self.agent_l2_label[
                                                      vn_fq_name],
                                                  cn_l2_routes[0]['label']))
            # end for
        return True
    # end verify_l2_routes_in_control_nodes

    @retry(delay=2, tries=25)
    def verify_vm_not_in_control_nodes(self):
        ''' Validate that routes for VM is removed in control-nodes.

        '''
        result = True
        self.verify_vm_not_in_control_nodes_flag = True

        for vn_fq_name in self.vn_fq_names:
            ri_name = vn_fq_name + ':' + vn_fq_name.split(':')[-1]
            for cn in self.get_ctrl_nodes_in_rt_group():
                # Check for VM route in each control-node
                for vm_ip in self.vm_ip_dict[vn_fq_name]:
                    cn_routes = self.cn_inspect[cn].get_cn_route_table_entry(
                                               ri_name=ri_name, prefix=vm_ip)
                    if cn_routes is not None:
                        with self.printlock:
                            self.logger.warn("Control-node %s still seems to "
                                             "have route for VMIP %s" % (cn, vm_ip))
                        self.verify_vm_not_in_control_nodes_flag =\
                            self.verify_vm_not_in_control_nodes_flag and False
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
            _intf = self.analytics_obj.get_intf_uve(intf)
            if not _intf:
                return None
            vn_name = _intf['virtual_network']
            if vn_name == vn_fq_name:
                return ops_intf_list.index(intf)
        return None

    @retry(delay=2, tries=45)
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
                ops_index = self._get_ops_intf_index(ops_intf_list, vn_fq_name)
                if ops_index is None:
                    self.logger.error(
                        'VN %s is not seen in opserver for VM %s' %
                        (vn_fq_name, self.vm_id))
                    self.vm_in_op_flag = self.vm_in_op_flag and False
                    return False
                ops_intf = ops_intf_list[ops_index]
                #ops_data = self.analytics_obj.get_intf_uve(ops_intf)
                #ops_data = ops_intf_list[ops_index]
                for vm_ip in self.vm_ip_dict[vn_fq_name]:
                    try:
                        if is_v6(vm_ip):
                            op_data = self.analytics_obj.get_vm_attr(ops_intf,'ip6_address')
                        else:
                            op_data = self.analytics_obj.get_vm_attr(ops_intf,'ip_address')
                    except Exception as e:
                        return False

                    if vm_ip != op_data:
                        self.logger.warn(
                            "Opserver doesnt list IP Address %s of vm %s" % (
                                vm_ip, self.vm_name))
                        self.vm_in_op_flag = self.vm_in_op_flag and False
                        result = result and False
                # end if
                self.ops_vm_obj = self.ops_inspect[ip].get_ops_vm(self.vm_id)
        # end if
        self.logger.info("Verifying vm in vn uve")
        for intf in ops_intf_list:
            intf = self.analytics_obj.get_intf_uve(intf)
            virtual_network = intf['virtual_network']
            ip_address = [intf['ip_address'], intf['ip6_address']]
            #intf_name = intf['name']
            intf_name = intf
            self.logger.info("vm uve shows interface as %s" % (intf_name))
            self.logger.info("vm uve shows ip address as %s" %
                             (ip_address))
            self.logger.info("vm uve shows virtual netowrk as %s" %
                             (virtual_network))
            vm_in_vn_uve = self.analytics_obj.verify_vn_uve_for_vm(
                vn_fq_name=virtual_network, vm=self.vm_id)
            if not vm_in_vn_uve:
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
                "Collectors doesnt have consistent info for vm uve")
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
                        dct.update({vn_fq_name: vrf_id[0]})
                if dct:
                    vrfs[ip] = dct
        except Exception as e:
            self.logger.exception('Exception while getting VRF id')
        finally:
            return vrfs

    def cleanUp(self):
        super(VMFixture, self).cleanUp()
        self.delete()

    def delete(self, verify=False):
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            if len(self.port_ids)!=0:
                for each_port_id in self.port_ids:
                    self.interface_detach(each_port_id)
            for vm_obj in list(self.vm_objs):
                for sec_grp in self.sg_ids:
                    self.logger.info("Removing the security group"
                                     " from VM %s" % (vm_obj.name))
                    self.remove_security_group(sec_grp)
                self.logger.info("Deleting the VM %s" % (vm_obj.name))
                if self.inputs.is_gui_based_config():
                    self.webui.delete_vm(self)
                else:
                    self.orch.delete_vm(vm_obj)
                    self.vm_objs.remove(vm_obj)
            time.sleep(5)
            self.verify_cleared_from_setup(verify=verify)
        else:
            self.logger.info('Skipping the deletion of VM %s' %
                             (self.vm_name))
    # end cleanUp

    def verify_cleared_from_setup(self, check_orch=True, verify=False):
        # Not expected to do verification when self.count is > 1, right now
        if self.verify_is_run or verify:
             assert self.verify_vm_not_in_api_server()
             if check_orch:
                 assert self.verify_vm_not_in_orchestrator()
             assert self.verify_vm_not_in_agent()
             assert self.verify_vm_not_in_control_nodes()
             assert self.verify_vm_not_in_nova()

             assert self.verify_vm_flows_removed()
             for vn_fq_name in self.vn_fq_names:
                  self.analytics_obj.verify_vm_not_in_opserver(
                        self.vm_id,
                        self.inputs.host_data[self.vm_node_ip]['name'],
                        vn_fq_name)

             # Trying a workaround for Bug 452
        # end if
        return True

    @retry(delay=2, tries=25)
    def verify_vm_not_in_nova(self):
        result = True
        self.verify_vm_not_in_nova_flag = True
        # In environments which does not have mysql token file, skip the check
        if not self.inputs.get_mysql_token():
            return result
        for vm_obj in self.vm_objs:
            result = result and self.orch.is_vm_deleted(vm_obj)
            self.verify_vm_not_in_nova_flag =\
                self.verify_vm_not_in_nova_flag and result
        return result
    # end verify_vm_not_in_nova

    def tftp_file_to_vm(self, file, vm_ip):
        '''Do a tftp of the specified file to the specified VM

        '''
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        if "TEST_DELAY_FACTOR" in os.environ:
            delay_factor = os.environ.get("TEST_DELAY_FACTOR")
        else:
            delay_factor = "1.0"
        timeout = math.floor(40 * float(delay_factor))
        try:
            with hide('everything'):
                with settings(host_string='%s@%s' % (
                              host['username'], self.vm_node_ip),
                              password=host['password'],
                              warn_only=True, abort_on_prompts=False):
                    if os.environ.has_key('ci_image'):
                        i = 'tftp -p -r %s -l %s %s' % (file, file, vm_ip)
                    else:
                        i = 'timeout %d atftp -p -r %s -l %s %s' % (timeout,
                                                                    file, file, vm_ip)
                    self.run_cmd_on_vm(cmds=[i], timeout=timeout + 10)
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
            self.orch.put_key_file_to_host(self.vm_node_ip)
            with hide('everything'):
                with settings(host_string='%s@%s' % (
                              host['username'], self.vm_node_ip),
                              password=host['password'],
                              warn_only=True, abort_on_prompts=False):
                    self.get_rsa_to_vm()
                    i = 'timeout %d scp -o StrictHostKeyChecking=no -i id_rsa %s %s@[%s]:' % (
                        timeout, file, dest_vm_username, vm_ip)
                    cmd_outputs = self.run_cmd_on_vm(
                        cmds=[i], timeout=timeout + 10)
                    self.logger.debug(cmd_outputs)
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying to scp the file ')
    # end scp_file_to_vm

    def put_pub_key_to_vm(self):
        self.logger.debug('Copying public key to VM %s' % (self.vm_name))
        self.orch.put_key_file_to_host(self.vm_node_ip)
        auth_file = '.ssh/authorized_keys'
        self.run_cmd_on_vm(['mkdir -p ~/.ssh'])
        host = self.inputs.host_data[self.vm_node_ip]
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (host['username'], self.vm_node_ip),
                password=host['password'],
                    warn_only=True, abort_on_prompts=False):
                fab_put_file_to_vm(host_string='%s@%s' % (
                    self.vm_username, self.local_ip),
                    password=self.vm_password,
                    src='/tmp/id_rsa.pub', dest='/tmp/')
        cmds = [
            'cat /tmp/id_rsa.pub >> ~/%s' % (auth_file),
            'chmod 600 ~/%s' % (auth_file),
            'cat /tmp/id_rsa.pub >> /root/%s' % (auth_file),
            'chmod 600 /root/%s' % (auth_file),
            'chown %s ~/%s' % (self.vm_username, auth_file),
            'chgrp %s ~/%s' % (self.vm_username, auth_file),
            '''sed -i -e 's/no-port-forwarding.*sleep 10\" //g' ~root/.ssh/authorized_keys''']
        self.run_cmd_on_vm(cmds, as_sudo=True)

    @retry(delay=10, tries=5)
    def check_file_transfer(self, dest_vm_fixture, dest_vn_fq_name=None, mode='scp',
                            size='100', fip=None, expectation=True, af=None):
        '''
        Creates a file of "size" bytes and transfers to the VM in dest_vm_fixture using mode scp/tftp
        '''
        filename = 'testfile'
        # Create file
        cmd = 'dd bs=%s count=1 if=/dev/zero of=%s' % (size, filename)
        self.run_cmd_on_vm(cmds=[cmd], as_sudo=True)

        if fip:
            dest_vm_ips = [fip]
        else:
            dest_vm_ips = dest_vm_fixture.get_vm_ips(
                vn_fq_name=dest_vn_fq_name, af=af)
        if mode == 'scp':
            dest_vm_fixture.run_cmd_on_vm(
                cmds=['cp -f ~root/.ssh/authorized_keys ~/.ssh/'], as_sudo=True)
            absolute_filename = filename
        elif mode == 'tftp':
            # Create the file on the remote machine so that put can be done
            absolute_filename = '/var/lib/tftpboot/' + filename
            dest_vm_fixture.run_cmd_on_vm(
                cmds=['sudo touch %s' % (absolute_filename),
                      'sudo chmod 777 %s' % (absolute_filename)])
        else:
            self.logger.error('No transfer mode specified!!')
            return False

        for dest_vm_ip in dest_vm_ips:
            if mode == 'scp':
                self.scp_file_to_vm(filename, vm_ip=dest_vm_ip,
                                        dest_vm_username=dest_vm_fixture.vm_username)
            else:
                self.tftp_file_to_vm(filename, vm_ip=dest_vm_ip)
            self.run_cmd_on_vm(cmds=['sync'])
            # Verify if file size is same
            out_dict = dest_vm_fixture.run_cmd_on_vm(
                cmds=['wc -c %s' % (absolute_filename)])
            if size in out_dict.values()[0]:
                self.logger.info('File of size %s is trasferred successfully to \
                        %s by %s ' % (size, dest_vm_ip, mode))
                if not expectation:
                    return False
            else:
                self.logger.warn('File of size %s is not trasferred fine to %s \
                        by %s' % (size, dest_vm_ip, mode))
                dest_vm_fixture.run_cmd_on_vm(
                    cmds=['rm -f %s' % (absolute_filename)])
                if mode == 'tftp':
                    dest_vm_fixture.run_cmd_on_vm(
                        cmds=['sudo touch %s' % (absolute_filename),
                              'sudo chmod 777 %s' % (absolute_filename)])
                if expectation:
                    return False
        return True
    # end check_file_transfer

    def get_rsa_to_vm(self):
        '''Get the rsa file to the VM from the agent

        '''
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        try:
            self.orch.put_key_file_to_host(self.vm_node_ip)
            with hide('everything'):
                with settings(
                    host_string='%s@%s' % (
                        host['username'], self.vm_node_ip),
                    password=host['password'],
                        warn_only=True, abort_on_prompts=False):
                    key_file = self.orch.get_key_file()
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

    def config_via_netconf(self, cmds=None):
        '''run cmds on VM
        '''
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        try:
            self.orch.put_key_file_to_host(self.vm_node_ip)
            fab_connections.clear()
            with hide('everything'):
                with settings(
                    host_string='%s@%s' % (host['username'], self.vm_node_ip),
                    password=host['password'],
                        warn_only=True, abort_on_prompts=False):
                    self.logger.debug('Running Cmd on %s' %
                                      self.vm_node_ip)
                    output = run_netconf_on_node(
                        host_string='%s@%s' % (
                            self.vm_username, self.local_ip),
                        password=self.vm_password,
                        cmds=cmds)
            return output
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying ping from VM')
            return False
   # end get_config_via_netconf

    def run_cmd_on_vm(self, cmds=[], as_sudo=False, timeout=30, as_daemon=False):
        '''run cmds on VM

        '''
        self.return_output_cmd_dict = {}
        self.return_output_values_list = []
        cmdList = cmds
        host = self.inputs.host_data[self.vm_node_ip]
        output = ''
        try:
            self.orch.put_key_file_to_host(self.vm_node_ip)
            fab_connections.clear()
            with hide('everything'):
                with settings(
                    host_string='%s@%s' % (host['username'], self.vm_node_ip),
                    password=host['password'],
                        warn_only=True, abort_on_prompts=False):
                    for cmd in cmdList:
                        self.logger.debug('Running Cmd on %s: %s' % (
                            self.vm_node_ip, cmd))
                        output = run_fab_cmd_on_node(
                            host_string='%s@%s' % (
                                self.vm_username, self.local_ip),
                            password=self.vm_password,
                            cmd=cmd,
                            as_sudo=as_sudo,
                            timeout=timeout,
                            as_daemon=as_daemon)
                        self.logger.debug(output)
                        self.return_output_values_list.append(output)
                    self.return_output_cmd_dict = dict(
                        zip(cmdList, self.return_output_values_list))
            return self.return_output_cmd_dict
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying ping from VM')
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
        result = result and self.wait_for_ssh_on_vm()
        if not result:
            self.logger.error('VM %s does not seem to be fully up' % (
                              self.vm_name))
            self.logger.error('Console output: %s' % self.get_console_output())
            return result
        return True
    # end wait_till_vm_is_up

    def scp_file_transfer_cirros(self, dest_vm_fixture, fip=None, size='100'):
        '''
        Creates a file of "size" bytes and transfers to the VM in dest_vm_fixture using mode scp/tftp
        '''
        filename = 'testfile'
        dest_vm_ip = dest_vm_fixture.vm_ip
        import pexpect
        # Create file
        cmd = 'dd bs=%s count=1 if=/dev/zero of=%s' % (size, filename)
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
            handle = pexpect.spawn(
                'ssh -F /dev/null -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null %s@%s' % (self.vm_username, self.local_ip))
            handle.timeout = int(timeout)
            i = handle.expect(['\$ ', 'password:'])
            if i == 0:
                pass
            if i == 1:
                handle.sendline('cubswin:)')
                handle.expect('\$ ')
            if fip:
                handle.sendline('scp %s %s@%s:~/.' %
                                (filename, dest_vm_fixture.vm_username, fip))
            else:
                handle.sendline(
                    'scp %s %s@%s:~/.' % (filename, dest_vm_fixture.vm_username, dest_vm_fixture.vm_ip))
            i = handle.expect(
                ['Do you want to continue connecting', '[P,p]assword'])
            if i == 0:
                handle.sendline('y')
                handle.expect('[P,p]assword')
                handle.sendline('cubswin:)')
            elif i == 1:
                handle.sendline('cubswin:)')
            else:
                self.logger.warn('scp file to VM failed')
            out_dict = dest_vm_fixture.run_cmd_on_vm(
                cmds=['ls -l %s' % (filename)])
            if size in out_dict.values()[0]:
                self.logger.info('File of size %s is trasferred successfully to \
                                  %s ' % (size, dest_vm_fixture.vm_name))
                return True
            else:
                self.logger.warn('File of size %s is not trasferred fine to %s \
                                 !! Pls check logs' % (size, dest_vm_fixture.vm_name))
                return False

    # end scp_file_transfer_cirros

    def get_console_output(self):
        return self.orch.get_console_output(self.vm_obj)

    @retry(delay=5, tries=20)
    def wait_for_ssh_on_vm(self):
        self.logger.info('Waiting to SSH to VM %s, IP %s' % (self.vm_name,
                                                             self.vm_ip))
        host = self.inputs.host_data[self.vm_node_ip]
        with settings(host_string='%s@%s' % (host['username'],
                      self.vm_node_ip), password=host['password'],
                      warn_only=True, abort_on_prompts=False):
            # Check if ssh from compute node to VM works(with retries)
            if fab_check_ssh('@'.join([self.vm_username, self.local_ip]),
                             self.vm_password):
                self.logger.info('VM %s is ready for SSH connections'%(
                                                         self.vm_name))
                return True
        self.logger.error('VM %s is NOT ready for SSH connections'%(
                                                      self.vm_name))
        return False
    # end wait_for_ssh_on_vm

    def copy_file_to_vm(self, localfile, dstdir):
         host = self.inputs.get_host_ip(self.vm_node_ip)
         filename = localfile.split('/')[-1]
         remotefile = dstdir+'/'+filename
         self.inputs.copy_file_to_server(host, localfile, '/tmp/', filename)
         cmd = 'fab -u %s -p "%s" -H %s ' % (
            self.vm_username, self.vm_password, self.local_ip)
         cmd = cmd + 'fput:%s,%s'%('/tmp/'+filename, remotefile)
         self.inputs.run_cmd_on_server(host, cmd)

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
        self.orch.put_key_file_to_host(self.vm_node_ip)
        key = self.orch.get_key_file()
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
        # May be we could match on NH index along with IP
        return result
        self.vm_flows_removed_flag = True
        output = self.inputs.run_cmd_on_server(self.vm_node_ip, cmd,
                                               self.inputs.host_data[
                                                   self.vm_node_ip]['username'],
                                               self.inputs.host_data[self.vm_node_ip]['password'])
        matches = [x for x in self.vm_ips if '%s:' % x in output]
        if matches:
            self.logger.warn(
                "One or more flows still present on Compute node after VM delete : %s" % (output))
            result = False
        else:
            self.logger.info("All flows for the VM deleted on Compute node")
        self.vm_flows_removed_flag = self.vm_flows_removed_flag and result
        return result
    # end verify_vm_flows_removed

    def start_webserver(self, listen_port=8000, content=None):
        '''Start Web server on the specified port.
        '''
        host = self.inputs.host_data[self.vm_node_ip]
        fab_connections.clear()
        try:
            with settings(host_string='%s@%s'%(host['username'],
                          self.vm_node_ip), password=host['password'],
                              warn_only=True, abort_on_prompts=False):
                    vm_host_string = '%s@%s'%(self.vm_username, self.local_ip)
                    cmd = 'echo %s >& index.html'%(content or self.vm_name)
                    output = run_fab_cmd_on_node(host_string=vm_host_string,
                                                 password=self.vm_password,
                                                 cmd=cmd)
                    cmd = 'python -m SimpleHTTPServer %d &> /dev/null'%listen_port
                    output = run_fab_cmd_on_node(host_string=vm_host_string,
                                                 password=self.vm_password,
                                                 cmd=cmd, as_daemon=True)
                    self.logger.debug(output)
        except Exception, e:
            self.logger.exception(
                'Exception occured while starting webservice on VM')
            return False
    # end webserver

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
        self.cs_vmi_obj = {}
        self.get_vmi_objs()
        self.vm_id = self.vm_objs[0].id
        # Figure out the local metadata IP of the VM reachable from host
        inspect_h = self.agent_inspect[self.vm_node_ip]

        cfgm_ip = self.inputs.cfgm_ips[0]
        api_inspect = self.api_s_inspects[cfgm_ip]
        vmi_objs = self.get_vmi_obj_from_api_server(cfgm_ip, refresh=True)[1]
        for vmi_obj in vmi_objs:
            vmi_vn_fq_name = ':'.join(
                vmi_obj['virtual-machine-interface']['virtual_network_refs'][0]['to'])
            self.cs_vmi_obj[vmi_vn_fq_name] = vmi_obj

        for vn_fq_name in self.vn_fq_names:
            (domain, project, vn) = vn_fq_name.split(':')
            vna_tap_id = inspect_h.get_vna_tap_interface_by_vmi(
                vmi_id=self.cs_vmi_obj[vn_fq_name][
                    'virtual-machine-interface']['uuid'])
            self.tap_intf[vn_fq_name] = vna_tap_id[0]
            self.tap_intf[vn_fq_name] = inspect_h.get_vna_intf_details(
                self.tap_intf[vn_fq_name]['name'])[0]
            if 'Active' not in self.tap_intf[vn_fq_name]['active']:
                self.logger.warn('VMI %s status is not active, it is %s' % (
                    self.tap_intf[vn_fq_name]['name'],
                    self.tap_intf[vn_fq_name]['active']))
                return False
            self.local_ips[vn_fq_name] = self.tap_intf[
                vn_fq_name]['mdata_ip_addr']
            self.mac_addr[vn_fq_name] = self.tap_intf[vn_fq_name]['mac_addr']
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
        return self.orch.wait_till_vm_status(self.vm_obj, status)

    def wait_till_vm_boots(self):
        return self.nova_h.wait_till_vm_is_up(self.vm_obj)

    def get_arp_entry(self, ip_address=None, mac_address=None):
        out_dict = self.run_cmd_on_vm(["arp -an"])
        return search_arp_entry(out_dict.values()[0], ip_address, mac_address)
    # end get_arp_entry

    def get_gateway_ip(self):
        cmd = '''netstat -anr  |grep ^0.0.0.0 | awk '{ print \\\\$2 }' '''
        out_dict = self.run_cmd_on_vm([cmd])
        return out_dict.values()[0].rstrip('\r')
    # end get_gateway_ip

    def get_gateway_mac(self):
        return self.get_arp_entry(ip_address=self.get_gateway_ip())[1]

    def migrate(self, compute):
        self.orch.migrate_vm(self.vm_obj, compute)

    def start_tcpdump(self, interface=None, filters=''):
        ''' This is similar to start_tcpdump_for_vm_intf() in tcpdump_utils.py
            But used here too, for ease of use
        '''
        if not interface:
            interface = self.tap_intf.values()[0]['name']
        compute_ip = self.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        
        (session, pcap) = start_tcpdump_for_intf(compute_ip, compute_user,
            compute_password, interface, filters, self.logger)
        return (session, pcap)
    # end start_tcpdump

    def stop_tcpdump(self, session, pcap):
        stop_tcpdump_for_intf(session, pcap, self.logger)

    def get_vm_interface_name(self, mac_address=None):
        ''' 
            Given a MAC address, returns the corresponding interface name
            in the VM

            Note that ifconfig output for some distros like fedora is diff 
            from that in Ubuntu/Cirros
            Ubuntu has ifconfig with format 
                p1p2      Link encap:Ethernet  HWaddr 00:25:90:c3:0a:f3

            and redhat-based distros has
            virbr0: flags=4099<UP,BROADCAST,MULTICAST>  mtu 1500
            inet 192.168.122.1  netmask 255.255.255.0  broadcast 192.168.122.255
            ether 42:7b:49:5e:cf:12  txqueuelen 0  (Ethernet)
        '''
        if not mac_address:
            mac_address = self.mac_addr.values()[0]
        if mac_address in self._vm_interface.keys():
            return self._vm_interface[mac_address]
        ubuntu_cmd = 'ifconfig | grep "%s" | awk \'{print \\\\$1}\' | head -1' %(
            mac_address)
        redhat_cmd = 'ifconfig | grep -i -B 2 "%s" | grep flags | '\
                        'awk \'{print \\\\$1}\'' % (mac_address)
        cmd = 'test -f /etc/redhat-release && %s || %s' % (redhat_cmd, 
            ubuntu_cmd)
        name = self.run_cmd_on_vm([cmd]).strip(':')
        self._vm_interface[mac_address] = name 
        return name
    # end get_vm_interface_name

    def arping(self, ip, interface=None):
        if not interface:
            interface_mac = self.mac_addr.values()[0]
            interface = self.get_vm_interface_name(interface_mac)

        cmd = 'arping -i %s -c 1 -r %s' % (interface, ip)
        outputs = self.run_cmd_on_vm([cmd])
        self.logger.debug('On VM %s, arping to %s on %s returned :%s' % (
            self.vm_name, ip, interface, outputs[0]))
        return (outputs[0].succeeded, outputs[0])
    # end arping

    def run_dhclient(self, interface=None):
        if not interface:
            interface_mac = self.mac_addr.values()[0]
            interface = self.get_vm_interface_name(interface_mac)
        cmds = ['dhclient -r %s ; dhclient %s' % (interface, interface)]
        outputs = self.run_cmd_on_vm(cmds, as_sudo=True, timeout=10)
        self.logger.debug('On VM %s, dhcp on %s returned :%s' % (
            self.vm_name, interface, outputs[0]))
        return (outputs[0].succeeded, outputs[0])
    # end run_dhclient

    def add_static_arp(self, ip, mac):
        self.run_cmd_on_vm(['arp -s %s %s' % (ip, mac)], as_sudo=True)
        self.logger.info('Added static arp %s:%s on VM %s' % (ip, mac,
                                                              self.vm_name))
    # end add_static_arp
        
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
                 vm_count_per_vn=2, flavor=None, project_name=None):
        """
        vms     : List of dictionaries of VMData objects.
        or
        vn_objs : List of tuples of VN name and VNfixture.obj returned by the
                  get_all_fixture method of MultipleVNFixture.

        """

        self.connections = connections
        self.nova_h = self.connections.nova_h
        if not project_name:
            project_name = connections.inputs.project_name
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

    def wait_for_ssh_on_vm(self):

        result = True
        for vm_name, vm_fixture in self._vm_fixtures:
            result &= vm_fixture.wait_for_ssh_on_vm()

        return result

    def wait_till_vm_is_up(self):

        result = True
        for vm_name, vm_fixture in self._vm_fixtures:
            result &= vm_fixture.wait_till_vm_is_up()

        return result
