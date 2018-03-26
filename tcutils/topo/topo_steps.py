''' This module provides utils for setting up sdn topology given the topo inputs'''
import os
import copy
import fixtures
import topo_steps
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from vn_policy_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from user_test import UserFixture
from tcutils.agent.vna_introspect_utils import *
from topo_helper import *
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from netaddr import *
from common.policy import policy_test_helper
from svc_template_fixture import SvcTemplateFixture
from svc_instance_fixture import SvcInstanceFixture
from svc_hc_fixture import HealthCheckFixture
from security_group import SecurityGroupFixture
from physical_device_fixture import PhysicalDeviceFixture
from pif_fixture import PhysicalInterfaceFixture
from physical_router_fixture import PhysicalRouterFixture
from virtual_router_fixture import VirtualRouterFixture
from qos_fixture import QosForwardingClassFixture
from qos_fixture import QosConfigFixture
from alarm_test import AlarmFixture
from rbac_test import RbacFixture
from tor_fixture import ToRFixture
from vcpe_router_fixture import VpeRouterFixture
from interface_route_table_fixture import InterfaceRouteTableFixture
try:
    from webui_test import *
except ImportError:
    pass

def createUser(self):
    if not (
            (self.topo.username == 'admin' or self.topo.username is None) and (
            self.topo.project == 'admin')):
        self.user_fixture = self.useFixture(
            UserFixture(
                connections=self.connections,
                username=self.topo.username, password=self.topo.password))
    return self
# end createUser

def createProject(self):
    self.project_fixture = {}
    self.project_fixture[self.topo.project] = self.useFixture(
        ProjectFixture(
            project_name=self.topo.project,
            username=self.topo.username, password=self.topo.password,
            connections=self.connections))
    self.project_fixture[self.topo.project].set_user_creds(self.topo.username,
                                                           self.topo.password)
    if not (
            (self.topo.username == 'admin' or self.topo.username is None) and (
            self.topo.project == 'admin')):
        self.logger.info(
            "provision user %s with role as admin in tenant %s" %
            (self.topo.username, self.topo.project))
        self.user_fixture.add_user_to_tenant(
            self.topo.project,
            self.topo.username,
            'admin')
    self.project_connections = self.project_fixture[self.topo.project].get_project_connections()
    self.project_inputs = self.project_connections.inputs
    #update the af type for the new project
    self.project_inputs.set_af(self.inputs.get_af())
    #update new connection in project fixture 
    self.project_parent_fixt = self.useFixture(
        ProjectTestFixtureGen(self.vnc_lib, project_name=self.topo.project))
    if self.skip_verify == 'no':
        assert self.project_fixture[
            self.topo.project].verify_on_setup()
    return self
# end createProject


def createSec_group(self, option='contrail'):
    if option == 'openstack':
        create_sg_quantum(self)
    elif option == 'contrail':
        create_sg_contrail(self)
    else:
        self.logger.error("invalid config option %s" % option)
    return self
# end of createSec_group

def create_sg_quantum(self):
    if hasattr(self.topo, 'sg_list'):
        self.sg_uuid = {}
        self.secgrp_fixture = {}
        for sg_name in self.topo.sg_list:
            result = True
            msg = []
            self.secgrp_fixture[sg_name] = self.useFixture(
                SecurityGroupFixture(
		    connections=self.project_connections,
                    domain_name=self.topo.domain,
                    project_name=self.topo.project,
                    secgrp_name=sg_name,
                    secgrp_entries=self.topo.sg_rules[sg_name],option='neutron'))
            self.sg_uuid[sg_name] = self.secgrp_fixture[sg_name].secgrp_id
            if self.skip_verify == 'no':
                ret, msg = self.secgrp_fixture[sg_name].verify_on_setup()
                assert ret, "Verifications for security group is :%s failed and its error message: %s" % (
                    sg_name, msg)
    return self
# end of create_sg_quantum

def create_sg_contrail(self):
    if hasattr(self.topo, 'sg_list'):
        self.sg_uuid = {}
        self.secgrp_fixture = {}
        for sg_name in self.topo.sg_list:
            result = True
            msg = []
            self.secgrp_fixture[sg_name] = self.useFixture(
                SecurityGroupFixture(
                    connections=self.project_connections,
                    domain_name=self.topo.domain,
                    project_name=self.topo.project,
                    secgrp_name=sg_name,
                    secgrp_entries=self.topo.sg_rules[sg_name],option='contrail'))
            self.sg_uuid[sg_name] = self.secgrp_fixture[sg_name].secgrp_id
            if self.skip_verify == 'no':
                ret, msg = self.secgrp_fixture[sg_name].verify_on_setup()
                assert ret, "Verifications for security group is :%s failed and its error message: %s" % (
                    sg_name, msg)
    return self
# end of create_sg_contrail


def createPolicy(self, option='openstack'):
    if option == 'openstack' or self.inputs.orchestrator == 'vcenter':
        createPolicyFixtures(self)
    elif option == 'contrail':
        createPolicyContrail(self)
    else:
        self.logger.error("invalid config option %s" % option)
    return self
# end createPolicy


def createPolicyFixtures(self, option='openstack'):
    self.policy_fixt = {}
    self.conf_policy_objs = {}
    d = [p for p in self.topo.policy_list]
    to_be_created_pol = (p for p in d if d)
    for policy_name in to_be_created_pol:
        self.policy_fixt[policy_name] = self.useFixture(
            PolicyFixture(policy_name=policy_name,
                          rules_list=self.topo.rules[policy_name],
                          inputs=self.project_inputs,
                          connections=self.project_connections))
        if self.skip_verify == 'no':
            ret = self.policy_fixt[policy_name].verify_on_setup()
            if ret['result'] == False:
                self.logger.error(
                    "Policy %s verification failed after setup" % policy_name)
                assert ret['result'], ret['msg']
    for vn in self.topo.vnet_list:
        self.conf_policy_objs[vn] = []
        for policy_name in self.topo.vn_policy[vn]:
            self.conf_policy_objs[vn].append(
                self.policy_fixt[policy_name].policy_obj)
    return self
# end createPolicyOpenstack


def createPolicyContrail(self):
    self.policy_fixt = {}
    self.conf_policy_objs = {}
    d = [p for p in self.topo.policy_list]
    to_be_created_pol = (p for p in d if d)
    for policy_name in to_be_created_pol:
        self.policy_fixt[policy_name] = self.useFixture(
            NetworkPolicyTestFixtureGen(
                self.vnc_lib,
                network_policy_name=policy_name,
                parent_fixt=self.project_parent_fixt,
                network_policy_entries=PolicyEntriesType(
                    self.topo.rules[policy_name])))
        policy_read = self.vnc_lib.network_policy_read(
            id=str(self.policy_fixt[policy_name]._obj.uuid))
        if not policy_read:
            self.logger.error("Policy:%s read on API server failed" %
                              policy_name)
            assert False, "Policy %s read failed on API server" % policy_name
    for vn in self.topo.vnet_list:
        self.conf_policy_objs[vn] = []
        for policy_name in self.topo.vn_policy[vn]:
            self.conf_policy_objs[vn].append(
                self.policy_fixt[policy_name]._obj)
    return self
# end createPolicyContrail


def createIPAM(self, option='openstack'):
    track_created_ipam = []
    self.ipam_fixture = {}
    self.conf_ipam_objs = {}
    default_ipam_name = self.topo.project + "-default-ipam"
    if 'vn_ipams' in dir(self.topo):
        print "topology has IPAM specified, need to create for each VN"
        for vn in self.topo.vnet_list:
            self.conf_ipam_objs[vn] = []
            if vn in self.topo.vn_ipams:
                ipam_name = self.topo.vn_ipams[vn]
            else:
                ipam_name = default_ipam_name
            if ipam_name in track_created_ipam:
                if option == 'contrail':
                    self.conf_ipam_objs[vn] = self.ipam_fixture[ipam_name].obj
                else:
                    self.conf_ipam_objs[vn] = self.ipam_fixture[
                        ipam_name].fq_name
                continue
            print "creating IPAM %s" % ipam_name
            self.ipam_fixture[ipam_name] = self.useFixture(
                IPAMFixture(
                    connections=self.project_fixture[
                        self.topo.project].connections,
                    name=ipam_name))
            if self.skip_verify == 'no':
                assert self.ipam_fixture[
                    ipam_name].verify_on_setup(), "verification of IPAM:%s failed" % ipam_name
            track_created_ipam.append(ipam_name)
            if option == 'contrail':
                self.conf_ipam_objs[vn] = self.ipam_fixture[ipam_name].obj
            else:
                self.conf_ipam_objs[vn] = self.ipam_fixture[ipam_name].fq_name
    else:
        ipam_name = default_ipam_name
        print "creating project default IPAM %s" % ipam_name
        self.ipam_fixture[ipam_name] = self.useFixture(
            IPAMFixture(
                connections=self.project_fixture[
                    self.topo.project].connections,
                name=ipam_name))
        if self.skip_verify == 'no':
            assert self.ipam_fixture[
                ipam_name].verify_on_setup(), "verification of IPAM:%s failed" % ipam_name
        for vn in self.topo.vnet_list:
            if option == 'contrail':
                self.conf_ipam_objs[vn] = self.ipam_fixture[ipam_name].obj
            else:
                self.conf_ipam_objs[vn] = self.ipam_fixture[ipam_name].fq_name
    return self
# end createIPAM


def createVN_Policy(self, option='openstack'):
    if option == 'openstack':
        createVN_Policy_OpenStack(self)
    elif option == 'contrail':
        createVN_Policy_Contrail(self)
    else:
        self.logger.error("invalid config option %s" % option)
    return self
# end createVN_Policy


def createVN(self, option='openstack'):
    if option == 'openstack' or self.inputs.orchestrator == 'vcenter':
        createVNOrch(self)
    elif option == 'contrail':
        createVNContrail(self)
    else:
        self.logger.error("invalid config option %s" % option)
    return self
# end createVN


def createVNOrch(self):
    self.vn_fixture = {}
    self.vn_of_cn = {}
    for vn in self.topo.vnet_list:
	router_asn = None
	rt_number = None
	if hasattr(self.topo, 'vn_params'):	
	   if self.topo.vn_params.has_key(vn):
  	       if self.topo.vn_params[vn].has_key('router_asn'):
		    router_asn = self.topo.vn_params[vn]['router_asn']
               if self.topo.vn_params[vn].has_key('rt_number'):
                    rt_number = self.topo.vn_params[vn]['rt_number']

        self.vn_fixture[vn] = self.useFixture(
            VNFixture(project_name=self.topo.project,
                      connections=self.project_connections, vn_name=vn,
		      inputs=self.project_inputs, subnets=self.topo.vn_nets[vn],
                      ipam_fq_name=self.conf_ipam_objs[vn], router_asn=router_asn,
		      rt_number=rt_number))
        if self.skip_verify == 'no':
            ret = self.vn_fixture[vn].verify_on_setup()
            assert ret, "One or more verifications for VN:%s failed" % vn
    # Initialize compute's VN list
    for cn in self.inputs.compute_names:
        self.vn_of_cn[self.inputs.compute_info[cn]] = []
    return self
# end create_VN_only_OpenStack


def attachPolicytoVN(self, option='openstack'):
    self.vn_policy_fixture = {}
    for vn in self.topo.vnet_list:
        self.vn_policy_fixture[vn] = self.useFixture(
            VN_Policy_Fixture(
                connections=self.project_connections,
                vn_name=vn,
                vn_obj=self.vn_fixture,
                vn_policys=self.topo.vn_policy[vn],
                project_name=self.topo.project,
                options=option,
                policy_obj=self.conf_policy_objs))
        if self.skip_verify == 'no':
            ret = self.vn_fixture[vn].verify_on_setup()
            assert ret, "One or more verifications for VN:%s failed" % vn
            for policy_name in self.topo.vn_policy[vn]:
                ret = self.policy_fixt[policy_name].verify_on_setup()
                if ret['result'] == False:
                    self.logger.error(
                        "Policy %s verification failed after setup" %
                        policy_name)
                    assert ret['result'], ret['msg']
    return self
# end attachPolicytoVN


def attachPolicytoVN(self, option='contrail'):
    self.vn_policy_fixture = {}
    for vn in self.topo.vnet_list:
        self.vn_policy_fixture[vn] = self.useFixture(
            VN_Policy_Fixture(
                connections=self.project_connections,
                vn_name=vn,
                options=option,
                policy_obj=self.conf_policy_objs,
                vn_obj=self.vn_fixture,
                vn_policys=self.topo.vn_policy[vn],
                project_name=self.topo.project))
    return self
# end attachPolicytoVN


def createVNContrail(self):
    self.vn_fixture = {}
    self.vn_of_cn = {}
    
    for vn in self.topo.vnet_list:
        router_asn = None
        rt_number = None
        rt_obj = None
        if hasattr(self.topo, 'vn_params'):
           if self.topo.vn_params.has_key(vn):
               if self.topo.vn_params[vn].has_key('router_asn'):
                    router_asn = self.topo.vn_params[vn]['router_asn']
               if self.topo.vn_params[vn].has_key('rt_number'):
                    rt_number = self.topo.vn_params[vn]['rt_number']

               rt_val = "target:%s:%s" % (router_asn, rt_number)
               rt_obj = RouteTargetList([rt_val])

        for ipam_info in self.topo.vn_nets[vn]:
            ipam_info = list(ipam_info)
            ipam_info[0] = self.conf_ipam_objs[vn]
            ipam_info = tuple(ipam_info)
        self.vn_fixture[vn] = self.useFixture(
            VirtualNetworkTestFixtureGen(
                self.vnc_lib,
                virtual_network_name=vn,
                parent_fixt=self.project_parent_fixt,
                id_perms=IdPermsType(
                    enable=True),
                network_ipam_ref_infos=[ipam_info],
                route_target_list=rt_obj))
        vn_read = self.vnc_lib.virtual_network_read(
            id=str(self.vn_fixture[vn]._obj.uuid))
        if vn_read:
            self.logger.info("VN created successfully %s " % (vn))
        if not vn_read:
            self.logger.error("VN %s read on API server failed" % vn)
            assert False, "VN:%s read failed on API server" % vn
    # Initialize compute's VN list
    for cn in self.inputs.compute_names:
        self.vn_of_cn[self.inputs.compute_info[cn]] = []
    return self
# end createVNContrail


def createVN_Policy_OpenStack(self):
    self.vn_fixture = {}
    self.vn_of_cn = {}
    for vn in self.topo.vnet_list:
        self.vn_fixture[vn] = self.useFixture(
            VNFixture(
                project_name=self.topo.project,
                connections=self.project_connections,
                vn_name=vn,
                inputs=self.project_inputs,
                subnets=self.topo.vn_nets[vn],
                policy_objs=self.conf_policy_objs[vn],
                ipam_fq_name=self.conf_ipam_objs[vn]))
        if self.skip_verify == 'no':
            ret = self.vn_fixture[vn].verify_on_setup()
            assert ret, "One or more verifications for VN:%s failed" % vn
    # Initialize compute's VN list
    for cn in self.inputs.compute_names:
        self.vn_of_cn[self.inputs.compute_info[cn]] = []
    return self
# end createVN_Policy_OpenStack


def createVN_Policy_Contrail(self):
    self.vn_fixture = {}
    self.vn_of_cn = {}
    for vn in self.topo.vnet_list:
        ref_tuple = []
        for conf_policy in self.conf_policy_objs[vn]:
            ref_tuple.append(
                (conf_policy,
                 VirtualNetworkPolicyType(
                     sequence=SequenceType(
                         major=0,
                         minor=0))))
            for ipam_info in self.topo.vn_nets[vn]:
                ipam_info = list(ipam_info)
                ipam_info[0] = self.conf_ipam_objs[vn]
                ipam_info = tuple(ipam_info)
            self.vn_fixture[vn] = self.useFixture(
                VirtualNetworkTestFixtureGen(
                    self.vnc_lib,
                    virtual_network_name=vn,
                    parent_fixt=self.project_parent_fixt,
                    id_perms=IdPermsType(
                        enable=True),
                    network_policy_ref_infos=ref_tuple,
                    network_ipam_ref_infos=[ipam_info]))
            vn_read = self.vnc_lib.virtual_network_read(
                id=str(self.vn_fixture[vn]._obj.uuid))
            if not vn_read:
                self.logger.error("VN %s read on API server failed" % vn)
                assert False, "VN:%s read failed on API server" % vn
    # Initialize compute's VN list
    for cn in self.inputs.compute_names:
        self.vn_of_cn[self.inputs.compute_info[cn]] = []
    return self
# end createVN_Policy_Contrail


def createVMNova(
        self,
        option='openstack',
        vms_on_single_compute=False,
        VmToNodeMapping=None):
    self.vm_fixture = {}
    host_list = self.connections.orch.get_hosts()
    vm_image_name = self.inputs.get_ci_image() or 'ubuntu-traffic'

    for vm in self.topo.vmc_list:
        sec_gp = []
        if option == 'contrail':
            vn_read = self.vnc_lib.virtual_network_read(
                id=str(self.vn_fixture[self.topo.vn_of_vm[vm]].getObj().uuid))
            vn_obj = self.orch.get_vn_obj_if_present(
                vn_read.name,
                project_id=self.project_fixture[
                    self.topo.project].uuid)
        else:
            vn_obj = self.vn_fixture[self.topo.vn_of_vm[vm]].obj
        if hasattr(self.topo, 'sg_of_vm'):
            if self.topo.sg_of_vm.has_key(vm):
                for sg in self.topo.sg_of_vm[vm]:
                    sec_gp.append(self.sg_uuid[sg])
        else:
            pass
        if vms_on_single_compute:
            self.vm_fixture[vm] = self.useFixture(
                VMFixture(
                    project_name=self.topo.project,
                    connections=self.project_connections,
                    vn_obj=vn_obj,
                    flavor=self.flavor,
                    image_name=vm_image_name,
                    vm_name=vm,
                    sg_ids=sec_gp,
                    node_name=host_list[0]))
        else:
            # If vm is pinned to a node get the node name from node IP and pass
            # it on to VM creation method.
            if VmToNodeMapping is not None and len(VmToNodeMapping) != 0:
                IpToNodeName = self.inputs.host_data[
                    VmToNodeMapping[vm]]['name']
                self.vm_fixture[vm] = self.useFixture(
                    VMFixture(
                        project_name=self.topo.project,
                        connections=self.project_connections,
                        vn_obj=vn_obj,
                        flavor=self.flavor,
                        image_name=vm_image_name,
                        vm_name=vm,
                        sg_ids=sec_gp,
                        node_name=IpToNodeName))
            else:
                self.vm_fixture[vm] = self.useFixture(
                    VMFixture(
                        project_name=self.topo.project,
                        connections=self.project_connections,
                        vn_obj=vn_obj,
                        flavor=self.flavor,
                        image_name=vm_image_name,
                        sg_ids=sec_gp,
                        vm_name=vm))

    # We need to retry following section and scale it up if required (for slower VM environment)
    # TODO: Use @retry annotation instead
    if "TEST_RETRY_FACTOR" in os.environ:
        retry_factor = os.environ.get("TEST_RETRY_FACTOR")
    else:
        retry_factor = "1.0"
    retry_count = math.floor(5 * float(retry_factor))

    self.logger.debug(
        "Setup step: Verify VM status and install Traffic package... ")
    for vm in self.topo.vmc_list:
        assert self.vm_fixture[vm].wait_till_vm_is_up(),(
            'VM Failed to come up')
        #Even though VM verification is not run, we need to set verify_is_run
        #to make sure cleanup is verified in VM fixture
        self.vm_fixture[vm].verify_is_run = True
        vm_node_ip = self.vm_fixture[vm].vm_node_ip
        self.vn_of_cn[vm_node_ip].append(self.topo.vn_of_vm[vm])

    # Add compute's VN list to topology object based on VM creation
    self.topo.__dict__['vn_of_cn'] = self.vn_of_cn

    # Provision static route if defined in topology
    createStaticRouteBehindVM(self)

    return self
# end createVMNova


def createPublicVN(self):
    if 'public_vn' in dir(self.topo):
        fip_pool_name = self.inputs.fip_pool_name
        fvn_name = self.topo.public_vn
        fip_subnets = [self.inputs.fip_pool]
        mx_rt = self.inputs.mx_rt
        self.fvn_fixture = self.useFixture(
            VNFixture(
                project_name=self.topo.project,
                connections=self.project_connections,
                vn_name=fvn_name,
                inputs=self.project_inputs,
                subnets=fip_subnets,
                router_asn=self.inputs.router_asn,
                rt_number=mx_rt))
        assert self.fvn_fixture.verify_on_setup()
        self.logger.info('created public VN:%s' % fvn_name)
        self.fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.topo.project,
                inputs=self.project_inputs,
                connections=self.project_connections,
                pool_name=fip_pool_name,
                vn_id=self.fvn_fixture.vn_id,
                vn_name=fvn_name))
        assert self.fip_fixture.verify_on_setup()
        self.logger.info('created FIP Pool:%s under Project:%s' %
                         (fip_pool_name, self.topo.project))
        self.public_vn_present = True
    return self
# end createPublicVN


def verifySystemPolicy(self):
    result, err_msg = policy_test_helper.comp_rules_from_policy_to_system(self)
    self.result = result
    if err_msg:
        self.err_msg = err_msg
    else:
        self.err_msg = []
    return self.result, self.err_msg


def verify_fip_associate_possible(self, vm_cnt):
    self.cn_inspect = self.connections.cn_inspect
    if not self.public_vn_present:
        return False

    if len(self.inputs.ext_routers) >= 1:
        router_name = self.inputs.ext_routers[0][0]
        router_ip = self.inputs.ext_routers[0][1]
        for host in self.inputs.bgp_ips:
            # Verify the connection between all control nodes and MX(if
            # present)
            cn_bgp_entry = self.cn_inspect[host].get_cn_bgp_neigh_entry()
            if isinstance(cn_bgp_entry, type(dict())):
                if cn_bgp_entry['peer_address'] == router_ip:
                    if cn_bgp_entry['state'] != 'Established':
                        return False
            else:
                for entry in cn_bgp_entry:
                    if entry['peer_address'] == router_ip:
                        if entry['state'] != 'Established':
                            return False
    else:
        self.logger.info(
            'No MX connectivity exists for this setup, we can use normal way to pump traffic')
        return False
    fip_pool = IPNetwork(self.inputs.fip_pool)
    if fip_pool.size <= 3:
        self.logger.info(
            'FIP pool is not sufficient to allocate FIPs to all VM')
        return False
    if vm_cnt <= (fip_pool.size - 3):
        self.logger.info('FIP pool is sufficient to allocate FIPs to all VM')
        return True
    else:
        self.logger.info(
            'FIP pool is not sufficient to allocate FIPs to all VM')
        return False
# end verify_fip_associate_possible


def allocateNassociateFIP(self, config_topo):
    self.fip_ip_by_vm = {}
    for project in self.projectList:
        self.logger.info("Share public-pool with project:%s" % project)
        pool_share = self.fip_fixture.assoc_project(project)
        self.addCleanup(self.fip_fixture.deassoc_project, project)
        for vmfixt in config_topo[project]['vm']:
            if self.inputs.is_gui_based_config():
                self.fip_fixture.create_and_assoc_fip_webui(
                    self.fvn_fixture.vn_id,
                    config_topo[project]['vm'][vmfixt].vm_id)
            else:
                fip_id = self.fip_fixture.create_and_assoc_fip(
                    self.fvn_fixture.vn_id,
                    config_topo[project]['vm'][vmfixt].vm_id)
            assert self.fip_fixture.verify_fip(
                fip_id, config_topo[project]['vm'][vmfixt], self.fvn_fixture)
            self.fip_ip_by_vm[vmfixt] = config_topo[project]['vm'][
                vmfixt].chk_vmi_for_fip(vn_fq_name=self.fvn_fixture.vn_fq_name)
            self.addCleanup(self.fip_fixture.disassoc_and_delete_fip, fip_id)
    return self
# end allocateNassociateFIP


def createStaticRouteBehindVM(self):
    try:
        self.topo.vm_static_route
    except AttributeError:
        return self
    for vm_name in self.topo.vm_static_route:
        vm_fixt = self.vm_fixture[vm_name]
        prefix = self.topo.vm_static_route[vm_name]
        vm_uuid = vm_fixt.vm_id
        vm_ip = vm_fixt.vm_ip
        vm_tap_intf = vm_fixt.tap_intf
        vmi = vm_tap_intf[vm_fixt.vn_fq_name]
        vmi_id = vmi['uuid']
        vm_route_table_name = "%s_rt" % vm_name
        self.logger.info(
            "Provisioning static route %s behind vm - %s in project %s." %
            (prefix, vm_name, self.topo.project))
        self.vm_fixture[vm_name].provision_static_route(
            prefix=prefix,
            tenant_name=self.topo.project,
            virtual_machine_interface_id=vmi_id,
            route_table_name=vm_route_table_name,
            user=self.topo.username,
            password=self.topo.password)
    return self
# end createStaticRouteBehindVM

def createServiceTemplate(self):
    self.st_fixture = {}
    if not hasattr(self.topo, 'st_list'):
        return self

    for st_name in self.topo.st_list:
        self.st_fixture[st_name] = self.useFixture(
            SvcTemplateFixture(
                connections=self.project_connections,
                st_name=st_name,
                svc_img_name=self.topo.st_params[st_name]['svc_img_name'],
                service_type=self.topo.st_params[st_name]['service_type'],
                service_mode=self.topo.st_params[st_name]['service_mode'],
                svc_scaling=self.topo.st_params[st_name]['svc_scaling'],
                flavor=self.topo.st_params[st_name]['flavor'],
                if_details=self.topo.st_params[st_name]['if_details'],
                version=self.topo.st_params[st_name]['version']))
        if self.skip_verify == 'no':
            assert self.st_fixture[st_name].verify_on_setup()
    return self
# end createServiceTemplate

def checkNAddAdminRole(self):
    if not ((self.topo.username == 'admin' or self.topo.username == None) and (self.topo.project == 'admin')):
        self.logger.info("Adding user 'admin' to non-default tenant %s with admin role" %self.topo.project)
        self.user_fixture.add_user_to_tenant(self.topo.project, 'admin', 'admin')
    return self
#end checkNAddAdminRole 

def checkNAddAdminRole(self):
    if not (
            (self.topo.username == 'admin' or self.topo.username is None) and (
            self.topo.project == 'admin')):
        self.logger.info(
            "Adding user 'admin' to non-default tenant %s with admin role" %
            self.topo.project)
        self.user_fixture.add_user_to_tenant(
            self.topo.project,
            'admin',
            'admin')
    return self
# end checkNAddAdminRole


def createServiceInstance(self):
    self.si_fixture = {}
    if not hasattr(self.topo, 'si_list'):
        return self

    # For SVC case to work in non-admin tenant, link "admin" user
    checkNAddAdminRole(self)
    for si_name in self.topo.si_list:
        self.si_fixture[si_name] = self.useFixture(
            SvcInstanceFixture(
                connections=self.project_connections,
                si_name=si_name,
                svc_template=self.st_fixture[
                    self.topo.si_params[si_name]['svc_template']].st_obj,
                if_details=self.topo.si_params[si_name]['if_details']))

    self.logger.debug("Setup step: Verify Service Instances")
    for si_name in self.topo.si_list:
        # Irrespective of verify flag, run minimum verification to make sure SI is up..
        # Include retry to handle time taken by less powerful computes ..
        retry = 0
        while True:
            ret, msg = self.si_fixture[si_name].verify_si()
            retry += 1
            if ret or retry > 2:
                break
        # In case of failure, set verify flag to get more data, even if global
        # verify flag is diabled
        if not ret:
            self.skip_verify = 'no'

        if self.skip_verify == 'no':
            ret, msg = self.si_fixture[si_name].verify_on_setup(report=False)

        if not ret:
            m = "service instance %s verify failed after setup with error %s" % (
                si_name, msg)
            self.err_msg.append(m)
            assert ret, self.err_msg

    return self
# end createServiceInstance

def createServiceHealthCheck(self):
    self.shc_fixture = {}
    if not hasattr(self.topo, 'shc_list'):
        return self
    for shc_name in self.topo.shc_list:
        shc_param = self.topo.shc_params[shc_name]
        self.shc_fixture[shc_name] = self.useFixture(
            HealthCheckFixture(
                connections=self.project_connections,
                name = shc_name,
                hc_type = shc_param['hc_type'],
                probe_type = shc_param['probe_type'],
                delay = shc_param['delay'],
                timeout = shc_param['timeout'],
                max_retries = shc_param['max_retries'],
                http_url = shc_param['http_url']))
        if self.skip_verify == 'no':
            assert self.shc_fixture[shc_name].verify_on_setup()
    return self
# end createServiceHealthCheck

def createPhysicalRouter(self, pr_list, pr_params):
    self.pr_fixture = {}
    self.pr_list = pr_list
    self.pr_params = pr_params
    for self.pr_name in self.pr_list:
        self.pr_fixture[self.pr_name] = self.useFixture(
            PhysicalDeviceFixture(
                self.pr_name,
                self.pr_params[self.pr_name]['mgmt_ip'],
                vendor=self.pr_params[self.pr_name]['vendor'],
                model=self.pr_params[self.pr_name]['model'],
                ssh_username=self.pr_params[self.pr_name]['ssh_username'],
                ssh_password=self.pr_params[self.pr_name]['ssh_password'],
                tunnel_ip=self.pr_params[self.pr_name]['tunnel_ip'],
                set_netconf=self.pr_params[self.pr_name]['set_netconf'],
                connections=self.project_connections))
    return self
# end createPhysicalRouter

def createPhysicalInterface(self, config_topo):
    self.pif_fixture = {}
    if not hasattr(self.topo, 'pif_list'):
        return self
    for pif_name in self.topo.pif_list:
        self.pif_fixture[pif_name] = self.useFixture(
            PhysicalInterfaceFixture(
                pif_name,
                device_id=config_topo['pr'][self.pr_name].uuid,
                int_type=self.topo.pif_params[pif_name]['int_type'],
                connections=self.project_connections))
    return self
# end createPhysicalInterface

def createForwardingClass(self):
    if hasattr(self.topo, 'fc_list'):
        self.qos_fixture = {}
        for index, fc_name in enumerate(self.topo.fc_list):
            result = True
            msg = []
            self.qos_fixture[fc_name] = self.useFixture(
                QosForwardingClassFixture(
                    connections=self.project_connections,
                    name=fc_name,
                    index=index,
                    fc_id=self.topo.fc_params[fc_name]['fc_id'],
                    dscp=self.topo.fc_params[fc_name]['dscp'],
                    dot1p=self.topo.fc_params[fc_name]['dot1p'],
                    exp=self.topo.fc_params[fc_name]['exp'],
                    queue_num=self.topo.fc_params[fc_name]['queue_num']))
            if self.skip_verify == 'no':
                ret, msg = self.qos_fixture[fc_name].verify_on_setup()
                assert ret, "Verifications for forwarding class :%s has failed and its error message: %s" % (
                    fc_name, msg)
    return self
# end of create_forwarding_class

def createQos(self, glob_flag=False):
    if hasattr(self.topo, 'qos_list' or 'qos_glob_list'):
        self.qos_fixture = {}
        if glob_flag:
            qos_list_option = self.topo.qos_glob_list
            qos_params_option = self.topo.qos_glob_params
        else:
            qos_list_option = self.topo.qos_list
            qos_params_option = self.topo.qos_params
            qos_config_type = None
        for qos_name in qos_list_option:
            result = True
            msg = []
            qos_param = qos_params_option[qos_name]
            if 'qos_config_type' in qos_param.keys():
                qos_config_type = qos_param['qos_config_type']
            self.qos_fixture[qos_name] = self.useFixture(
                QosConfigFixture(
                    glob_flag,
                    connections=self.project_connections,
                    name=qos_name,
                    dscp_mapping=qos_param['dscp_mapping'],
                    exp_mapping=qos_param['exp_mapping'],
                    dot1p_mapping=qos_param['dot1p_mapping'],
                    default_fc_id=qos_param['default_fc_id'],
                    qos_config_type=qos_config_type))
            if self.skip_verify == 'no':
                ret, msg = self.qos_fixture[qos_name].verify_on_setup()
                assert ret, "Verifications for qos :%s has failed and its error message: %s" % (
                    qos_name, msg)
    return self
# end of create_qos


def allocNassocFIP(self, config_topo=None, assoc=True):
    # Need Floating VN fixture in current project and destination VM fixtures from all projects
    # topology rep: self.fvn_vm_map = {'project1':
    #                        {'vnet1':{'project1': ['vmc2'], 'project2': ['vmc4']}},
    #                        {'vnet2':{'project1': ['vmc21'], 'project2': ['vmc14']}}
    if not config_topo:
            config_topo = self.config_topo
    for vn_proj, fvn_vm_map in self.topo.fvn_vm_map.iteritems():
        for vn_name, map in fvn_vm_map.iteritems():
            # {'project1': ['vmc2', 'vmc3'], 'project2': ['vmc4']},
            for vm_proj, vm_list in map.iteritems():
                for index in range(len(vm_list)):
                    # Get VM fixture from config_topo
                    vm_fixture = config_topo[
                        vm_proj]['vm'][vm_list[index]]
                    self.vn_fixture = config_topo[vn_proj]['vn']
                    self.logger.info(
                        'Allocating and associating FIP from %s VN pool in project %s to %s VM in project %s' %
                        (vn_name, vn_proj, vm_list[index], vm_proj))
                    if self.inputs.is_gui_based_config():
                        self.fip_fixture_dict[vn_name].alloc_and_assoc_fip_webui(
                            self.vn_fixture[vn_name].vn_id,
                            self.vm_fixture[self.topo.fvn_vm_map_dict[vn_name][index]].vm_id,
                            self.vm_fixture[self.topo.fvn_vm_map_dict[vn_name][index]].vm_ip,
                            self.topo.fvn_vm_map_dict[vn_name], assoc)
                        self.addCleanup(
                            self.fip_fixture_dict[vn_name].disassoc_and_delete_fip_webui,
                            self.vm_fixture[self.topo.fvn_vm_map_dict[vn_name][index]].vm_id,
                            self.vm_fixture[self.topo.fvn_vm_map_dict[vn_name][index]].vm_ip,
                            assoc)
                    else:
                        assigned_fip = vm_fixture.chk_vmi_for_fip(
                            vn_fq_name=self.vn_fixture[vn_name].vn_fq_name)
                        fip_id = self.fip_fixture_dict[vn_name].create_and_assoc_fip(
                            self.vn_fixture[vn_name].vn_id,
                            vm_fixture.vm_id)
                        if fip_id:
                            assert self.fip_fixture_dict[vn_name].verify_fip(
                                fip_id, vm_fixture, self.vn_fixture[vn_name])
                            self.logger.info('alloc&assoc FIP %s' % (fip_id))
                            self.addCleanup(
                                self.fip_fixture_dict[vn_name].deassoc_project,
                                vn_proj)
                            self.addCleanup(
                                self.fip_fixture_dict[vn_name].disassoc_and_delete_fip,
                                fip_id)
                        else:
                            # To handle repeat test runs without config cleanup, in which case, new FIP is assigned to VMI every time causing pool exhaustion
                            # Need to revisit check to skip assigning FIP if VMI
                            # already has a FIP from FIP-VN's
                            self.logger.info(
                                'Ignoring create_and_assoc_fip error as it can happen due to FIP pool exhaustion..')

    return self
# end allocNassocFIP



def createAllocateAssociateVnFIPPools(self, config_topo=None, alloc=True):
    if 'fvn_vm_map' in dir(self.topo):
        if not config_topo:
            config_topo = self.config_topo
        # topology rep: self.fip_pools= {'project1': {'p1-vn1-pool1':
        # {'host_vn': 'vnet1', 'target_projects': ['project1', 'project2']}},
        for fip_proj, fip_info in self.topo.fip_pools.iteritems():
            for fip_pool_name, info in fip_info.iteritems():
                vn_name = info['host_vn']
                self.vn_fixture = config_topo[fip_proj]['vn']
                self.fip_fixture_dict[vn_name] = self.useFixture(
                    FloatingIPFixture(
                        project_name=fip_proj,
                        inputs=self.inputs,
                        connections=self.connections,
                        pool_name=fip_pool_name,
                        vn_id=self.vn_fixture[vn_name].vn_id,
                        vn_name=vn_name))
                assert self.fip_fixture_dict[vn_name].verify_on_setup()
                self.logger.info(
                    'created FIP Pool:%s in Virtual Network:%s under Project:%s' %
                    (fip_pool_name, self.fip_fixture_dict[vn_name].pub_vn_name, fip_proj))
        self.fvn_vm_map = True
        try:
            self.config_topo[fip_proj]['fip'][3] = True
            self.config_topo[fip_proj]['fip'][4] = self.fip_fixture_dict
        except TypeError:
            pass
        if alloc:
            allocNassocFIP(self, config_topo)
    return self
# end createAllocateAssociateVnFIPPools

def createBGPRouter(self):
    self.bgp_router_fixture = {}
    if not hasattr(self.topo, 'pr_params'):
        return self
    for bgp_router in self.topo.pr_list:
        self.bgp_router_fixture[bgp_router] = self.useFixture(
            PhysicalRouterFixture(bgp_router,
                self.topo.pr_params[bgp_router]['tunnel_ip'],
                connections=self.project_connections,
                inputs=self.project_inputs,
                vendor=self.topo.pr_params[bgp_router]['vendor'],
                router_type=self.topo.pr_params[bgp_router]['router_type'],
                source_port=self.topo.pr_params[bgp_router]['source_port'],
                auth_type=self.topo.pr_params[bgp_router]['auth_type'],
                auth_key=self.topo.pr_params[bgp_router]['auth_key'],
                hold_time=self.topo.pr_params[bgp_router]['hold_time']
                ))
    return self
# end createBGPRouter

def createVirtualRouter(self):
    self.vrouter_fixture = {}
    if not hasattr(self.topo, 'vrouter_params'):
        return self
    for vrouter in self.topo.vrouter_list:
        self.vrouter_fixture[vrouter] = self.useFixture(
            VirtualRouterFixture(vrouter,
                self.topo.vrouter_params[vrouter]['type'],
                self.topo.vrouter_params[vrouter]['ip'],
                connections=self.project_connections,
                inputs=self.project_inputs))
    return self
# end createVirtualRouter

def createAlarms(self):
    self.alarm_fixture = {}
    if not hasattr(self.topo, 'alarms_params'):
        return self
    for alarm in self.topo.alarms_list:
        self.alarm_fixture[alarm] = self.useFixture(
            AlarmFixture(self.project_connections,
                alarm_name=alarm,
                uve_keys=self.topo.alarms_params[alarm]['uve_keys'],
                alarm_severity=self.topo.alarms_params[alarm]['alarm_severity'],
                alarm_rules = self.topo.alarms_params[alarm]['operation'],
                operand1=self.topo.alarms_params[alarm]['operand1'],
                operand2=self.topo.alarms_params[alarm]['operand2'],
                description=alarm,
                parent_obj_type=self.topo.alarms_params[alarm]['parent_type']))
        self.alarm_fixture[alarm].create(self.alarm_fixture[alarm].alarm_rules)
    return self
# end createAlarms

def createRBAC(self):
    self.rbac_fixture = {}
    if not hasattr(self.topo, 'rbac_params'):
        return self
    for rbac in self.topo.rbac_list:
        self.rbac_fixture[rbac] = self.useFixture(
            RbacFixture(rbac,
                parent_type=self.topo.rbac_params[rbac]['parent_type'],
                rules=self.topo.rbac_params[rbac]['rules'],
                connections=self.project_connections))
    return self
# end createRBAC

def createOVSDBTORAgent(self):
    self.tor_fixture = {}
    if not hasattr(self.topo, 'pr_tor_list'):
        return self
    for tor in self.topo.pr_tor_list:
        self.tor_fixture[tor] = self.useFixture(
            ToRFixture(
                tor,
                self.topo.pr_tor_params[tor]['mgmt_ip'],
                vendor=self.topo.pr_tor_params[tor]['vendor'],
                model=self.topo.pr_tor_params[tor]['model'],
                tunnel_ip=self.topo.pr_tor_params[tor]['tunnel_ip'],
                tor_agent=self.topo.pr_tor_params[tor]['tor_agent'],
                tsn=self.topo.pr_tor_params[tor]['tsn'],
                tor_agent_opt=self.topo.pr_tor_params[tor]['tor_agent_opt'],
                tsn_opt=self.topo.pr_tor_params[tor]['tsn_opt'],
                set_tor=self.topo.pr_tor_params[tor]['set_tor'],
                connections=self.project_connections))
    return self
# end createOVSDBTORAgent

def createVCPERouter(self):
    self.vcpe_fixture = {}
    if not hasattr(self.topo, 'vcpe_list'):
        return self
    for vcpe in self.topo.vcpe_list:
        self.vcpe_fixture[vcpe] = self.useFixture(
            VpeRouterFixture(
                vcpe,
                self.topo.vcpe_params[vcpe]['mgmt_ip'],
                tunnel_ip=self.topo.vcpe_params[vcpe]['tunnel_ip'],
                set_vcpe=self.topo.vcpe_params[vcpe]['set_vcpe'],
                connections=self.project_connections))
    return self
# end createVCPERouter

def createIntfRouteTable(self):
    self.intf_fixture = {}
    if not hasattr(self.topo, 'intf_route_table_params'):
        return self
    for intf in self.topo.intf_route_table_list:
        self.intf_fixture[intf] = self.useFixture(
            InterfaceRouteTableFixture(
                connections=self.project_connections,
                inputs=self.project_inputs,
                name=intf,
                prefixes=self.topo.intf_route_table_params[intf]['prefixes'],
                community=self.topo.intf_route_table_params[intf]['community']))
    return self
# end createIntfRouteTable

if __name__ == '__main__':
    ''' Unit test to invoke sdn topo setup utils.. '''

# end __main__
