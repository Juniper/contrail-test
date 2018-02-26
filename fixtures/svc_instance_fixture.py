import fixtures
from vnc_api.vnc_api import *
from tcutils.util import retry, get_random_name
from time import sleep
from tcutils.services import get_status
from vm_test import VMFixture
from svc_hc_fixture import HealthCheckFixture
try:
    from webui_test import *
except ImportError:
    pass


class SvcInstanceFixture(fixtures.Fixture):

    def __init__(self,
                 connections,
                 si_name,
                 svc_template,
                 if_details,
                 max_inst=1,
                 static_route=None,
                 availability_zone = None,
                 hc_list=None,
                 port_tuples_props=[]):
        '''
        svc_template : instance of ServiceTemplate
        '''
        self.static_route = static_route or { 'management':None,
                                              'left' : None,
                                              'right': None}
        self.port_tuples_props = port_tuples_props

        self.connections = connections
        self.vnc_lib = connections.vnc_lib
        self.api_s_inspect = connections.api_server_inspect
        self.nova_h = connections.nova_h
        self.domain_name = connections.domain_name
        self.project_name = connections.project_name
        self.si_name = si_name
        self.svc_template = svc_template
        self.st_name = svc_template.name
        self.si_version = svc_template.service_template_properties.version
        self.si_obj = None
        self.domain_fq_name = [self.domain_name]
        self.project_fq_name = [self.domain_name, self.project_name]
        self.si_fq_name = [self.domain_name, self.project_name, self.si_name]
        self.fq_name_str = ':'.join(self.si_fq_name)
        self.inputs = connections.inputs
        self.logger = self.inputs.logger
        self.already_present = False
        self.if_details = if_details
        self.max_inst = max_inst
        self.si = None
        self.svm_ids = []
        self.cs_svc_vns = []
        self.cs_svc_ris = []
        self.availability_zone = self.inputs.availability_zone or availability_zone
        self.svn_list = ['svc-vn-mgmt', 'svc-vn-left', 'svc-vn-right']
        self.hc_list = hc_list or [] # List of dicts of eg: [{'uuid': '1', 'intf_type': 'left'},
                                     #                       {'uuid': '2', 'intf_type': 'right'}]
        self._vnc = self.connections.orch.vnc_h
        if self.inputs.verify_thru_gui():
            self.browser = connections.browser
            self.browser_openstack = connections.browser_openstack
            self.webui = WebuiTest(connections, self.inputs)

        self.si_v2 = self.si_version == 2 or False
        self.si_v1 = self.si_version == 1 or False
        self.service_mode = svc_template.service_template_properties.service_mode
        self.port_tuples_uuids = []
        self.left_vn_fq_name = if_details.get('left', {}).get('vn_name', None)
        self.right_vn_fq_name = if_details.get(
            'right', {}).get('vn_name', None)
        self.mgmt_vn_fq_name = if_details.get(
            'management', {}).get('vn_name', None)
        self.intf_rt_table = []
        # Dict of svms with uuid as key
        self.svms = {}
    # end __init__

    def setUp(self):
        super(SvcInstanceFixture, self).setUp()
        self._create_si()
    # end setUp

    def cleanUp(self):
        super(SvcInstanceFixture, self).cleanUp()
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            if self.inputs.is_gui_based_config():
                self.webui.delete_svc_instance(self)
            else:
                self._delete_si()
            self.logger.info("Deleted SI %s" % (self.si_fq_name))
            assert self.verify_on_cleanup()
        else:
            self.logger.debug('Skipping deletion of SI %s' %
                              (self.si_fq_name))
    # end cleanUp

    def _create_si(self):
        try:
            svc_instance = self.vnc_lib.service_instance_read(
                fq_name=self.si_fq_name)
            self.already_present = True
            self.uuid = svc_instance.uuid
            self.logger.debug(
                "Service instance: %s already exists", self.si_fq_name)
        except NoIdError:
            self.logger.debug("Creating service instance: %s", self.si_fq_name)
            project = self.vnc_lib.project_read(fq_name=self.project_fq_name)
            svc_instance = ServiceInstance(self.si_name, parent_obj=project)
            si_type_args = None
            si_intf_type_args = {}
            left_vn_name = self.left_vn_fq_name.split(':')[-1] if self.left_vn_fq_name else None
            right_vn_name = self.right_vn_fq_name.split(':')[-1] if self.right_vn_fq_name else None
            mgmt_vn_name = self.mgmt_vn_fq_name.split(':')[-1] if self.mgmt_vn_fq_name else None
            si_prop = ServiceInstanceType(
                left_virtual_network=left_vn_name,
                right_virtual_network=right_vn_name,
                management_virtual_network=mgmt_vn_name)

            for itf in self.if_details:
                virtual_network = None
                if itf == 'left':
                    virtual_network = left_vn_name
                elif itf == 'right':
                    virtual_network = right_vn_name
                elif itf == 'management':
                    virtual_network = mgmt_vn_name

                if self.service_mode == 'transparent' and self.si_v1:
                    virtual_network = None
                if_type = ServiceInstanceInterfaceType(
                    virtual_network=virtual_network)
                si_prop.add_interface_list(if_type)

            svc_instance.set_service_instance_properties(si_prop)
            svc_instance.set_service_template(self.svc_template)
            if self.inputs.is_gui_based_config():
                self.webui.create_svc_instance(self)
            else:
                self.vnc_lib.service_instance_create(svc_instance)
            self.si_obj = self.vnc_lib.service_instance_read(
                fq_name=self.si_fq_name)
            for port_tuple_props in self.port_tuples_props:
                self.add_port_tuple(port_tuple_props)
            for hc in self.hc_list:
                self.associate_hc(hc['uuid'], hc['intf_type'])
            if self.static_route:
                self.associate_static_route_table(project, self.static_route)
        return self.si_obj
    # end _create_si

    def associate_static_route_table(self, project, static_rt_dict):
        for intf in static_rt_dict.keys():
            name = '%s_%s' % (self.si_name, intf)
            prefix = static_rt_dict[intf]
            if prefix:
                prefixes = prefix if type(prefix) is list else [prefix]
                self.logger.debug("Creating interface route table "
                                  "%s with prefixes %s"%(name, prefixes))
                intf_rt_table = self._vnc.create_interface_route_table(
                    name, parent_obj=project, prefixes=prefixes)
                self.logger.debug("Associating static route table %s to %s" % (
                    intf_rt_table.name, self.si_fq_name))
                self._vnc.assoc_intf_rt_table_to_si(
                    self.si_fq_name, intf_rt_table.uuid, intf)
                d = {'uuid': intf_rt_table.uuid, 'intf_type': intf}
                self.intf_rt_table.append(d)

    def disassociate_static_route_table(self, irt_uuid):
        self.logger.debug(
            "Disassociating static route table %s from %s" % (irt_uuid, self.si_fq_name))
        self._vnc.disassoc_intf_rt_table_from_si(self.si_fq_name, irt_uuid)
        self.logger.debug("Deleting interface route table %s"%irt_uuid)
        self._vnc.delete_interface_route_table(irt_uuid)

    def associate_hc(self, hc_uuid, intf_type):
        self.logger.debug("Associating hc(%s) to si (%s)" %
                          (hc_uuid, self.si_fq_name))
        self._vnc.assoc_health_check_to_si(self.si_fq_name, hc_uuid, intf_type)
        d = {'uuid': hc_uuid, 'intf_type': intf_type}
        if d not in self.hc_list:
            self.hc_list.append(d) 

    def disassociate_hc(self, hc_uuid):
        self.logger.debug(
            "Disassociating hc(%s) from si (%s)" % (hc_uuid, self.si_fq_name))
        self._vnc.disassoc_health_check_from_si(self.si_fq_name, hc_uuid)
        assert self.verify_hc_ref_not_in_vmi()
        for hc in list(self.hc_list):
            if hc['uuid'] == hc_uuid:
                self.hc_list.remove(hc)

    def _get_vn_of_intf_type(self, intf_type):
        if (intf_type == 'left'):
            return self.left_vn_fq_name
        elif (intf_type == 'right'):
            return self.right_vn_fq_name
        elif (intf_type == 'management'):
            return self.management_vn_fq_name

    def get_hc_status(self):
        if self.hc_list == []:
            return False
        for svm in self.svm_list:
            inspect_h = self.connections.agent_inspect[svm.vm_node_ip]
            for hc in self.hc_list:
                virtual_network = self._get_vn_of_intf_type(hc['intf_type'])
                vmi_id = svm.get_vmi_id(virtual_network)
                hc_obj = inspect_h.get_health_check(hc['uuid'])
                if not hc_obj or not vmi_id:
                    return False
                if not hc_obj.is_hc_active(vmi_id):
                    return False
        return True

    @retry(delay=2, tries=10)
    def verify_hc_is_active(self):
        return self.get_hc_status()

    @retry(delay=2, tries=10)
    def verify_hc_is_not_active(self):
        return not self.get_hc_status()

    @retry(delay=2, tries=10)
    def verify_hc_ref_not_in_vmi(self):
        for svm in self.svm_list:
            inspect_h = self.connections.agent_inspect[svm.vm_node_ip]
            for hc in self.hc_list:
                virtual_network = self._get_vn_of_intf_type(hc['intf_type'])
                vmi_id = svm.get_vmi_id(virtual_network)
                vmi_obj = self.vnc_lib.virtual_machine_interface_read(
                    id=vmi_id)
                hc_refs = vmi_obj.get_service_health_check_refs()
                if hc_refs:
                    for hc_ref in hc_refs:
                        if hc_ref['uuid'] == hc['uuid']:
                            self.logger.info('VMI has SHC refs')
                            return False
        return True
    # end verify_hc_ref_in_vmi

    @retry(delay=2, tries=10)
    def verify_hc_in_agent(self):
        for svm in self.svm_list:
            vm_node_ip = svm.vm_node_ip
            for hc in self.hc_list:
                hc_obj = self.useFixture(HealthCheckFixture(connections=self.connections,
                                                     uuid=hc['uuid']))
                if not hc_obj.verify_in_agent(vm_node_ip):
                    return False
        return True

    @retry(delay=2, tries=10)
    def verify_hc_not_in_agent(self, hc_list):
        for svm in self.svm_list:
            inspect_h = self.connections.agent_inspect[svm.vm_node_ip]
            for hc in hc_list:
                hc_obj = inspect_h.get_health_check(hc['uuid'])
                if hc_obj:
                    return False
        return True

    def _delete_si(self):
        curr_hc_list = list(self.hc_list)
        for hc in curr_hc_list:
            self.disassociate_hc(hc['uuid'])
        self.verify_hc_not_in_agent(curr_hc_list)
        intf_rt_table_list = list(self.intf_rt_table)
        for irt in intf_rt_table_list:
            self.disassociate_static_route_table(irt['uuid'])
        self.logger.debug("Deleting service instance: %s", self.si_fq_name)
        self.vnc_lib.service_instance_delete(fq_name=self.si_fq_name)
    # end _delete_si

    @property
    def svm_list(self):
        vms = getattr(self, '_svm_list', [])
        if not vms or len(vms) != len(self.svm_ids):
            # Reduce the svm_list to take care of reduce in ecmp instances
            self._svm_list = [vm for vm in vms if vm.get_uuid() in self.svm_ids]
            self.svms = {k:v for k,v in self.svms.items() if k in self.svm_ids}
            # Increase the svm_list to take care of increase in ecmp instances
            for vmid in set(self.svm_ids) - set([vm.get_uuid() for vm in self._svm_list]):
                vm = VMFixture(self.connections, uuid=vmid)
                vm.setUp()
                vm.wait_till_vm_is_active()
                # Populate tap intf details on the VM objects
                # Faster than calling wait_till_vm_is_up()
                if not vm.verify_vm_in_agent():
                    self.logger.error('VM %s not found in vrouter agent' %(
                        vmid))
                self._svm_list.append(vm)
                self.svms[vmid] = vm
        return self._svm_list

    def get_svms(self):
        return self.svm_list

    @retry(delay=2, tries=10)
    def verify_si(self):
        """check service instance"""
        self.project = self.vnc_lib.project_read(fq_name=self.project_fq_name)
        try:
            self.si = self.vnc_lib.service_instance_read(
                fq_name=self.si_fq_name)
            self.logger.debug(
                "Service instance: %s created succesfully", self.si_fq_name)
        except NoIdError:
            errmsg = "Service instance: %s not found." % self.si_fq_name
            self.logger.warn(errmsg)
            return (False, errmsg)
        return True, None

    @retry(delay=2, tries=10)
    def verify_st(self):
        """check service template"""
        self.cs_si = self.api_s_inspect.get_cs_si(
            domain=self.domain_name, project=self.project.name, si=self.si_name, refresh=True)
        try:
            st_refs = self.cs_si['service-instance']['service_template_refs']
        except KeyError:
            st_refs = None
        if not st_refs:
            errmsg = "No service template refs in SI '%s'" % self.si_name
            self.logger.warn(errmsg)
            return (False, errmsg)

        st_ref_name = [st_ref['to'][-1]
                       for st_ref in st_refs if st_ref['to'][-1] == self.st_name]
        if not st_ref_name:
            errmsg = "SI '%s' has no service template ref to %s" % (
                self.si_name, self.st_name)
            self.logger.warn(errmsg)
            return (False, errmsg)
        self.logger.debug("SI '%s' has service template ref to %s",
                          self.si_name, self.st_name)

        return True, None

    @retry(delay=5, tries=5)
    def verify_pt(self):
        """check Service PT"""
        self.cs_si = self.api_s_inspect.get_cs_si(
            domain=self.domain_name, project=self.project.name, si=self.si_name, refresh=True)
        try:
            self.pt_refs = self.cs_si[
                'service-instance']['port_tuples']
        except KeyError:
            self.pt_refs = None
        if not self.pt_refs:
            errmsg = "SI %s does not have any Port Tuple" % self.si_name
            self.logger.warn(errmsg)
            return (False, errmsg)
        self.pts = [pts['to'][-1] for pts in self.pt_refs]
        self.logger.debug("SI %s has Port Tuple:  %s", self.si_name, self.pts)
        return True, None

    def get_vm_refs(self):
        '''
        Returns a list of VM UUIDs referred by this SI
        '''
        vm_refs = None
        self.cs_si = self.api_s_inspect.get_cs_si(
            domain=self.domain_name,
            project=self.project.name,
            si=self.si_name,
            refresh=True)

        try:
            self.pt_refs = self.cs_si[
                'service-instance']['port_tuples']
        except KeyError:
            self.pt_refs = None

        if self.pt_refs:
            vm_refs = []
            for pt in self.pt_refs:
                cs_pt = self.api_s_inspect.get_cs_pt_by_id(pt['uuid'])
                pt_vmi_refs = cs_pt[
                    'port-tuple'].get('virtual_machine_interface_back_refs', [])
                for vmi in pt_vmi_refs:
                    vmi = self.api_s_inspect.get_cs_vmi_by_id(vmi['uuid'])
                    vm_refs_vmi = vmi[
                        'virtual-machine-interface'].get('virtual_machine_refs')
                    if not vm_refs_vmi:
                        msg = 'VM refs not seen in VMI %s' %(vmi)
                        self.logger.warn(msg)
                        return (None, msg)
                    for vm_ref in vm_refs_vmi:
                        vm_refs.append(vm_ref['to'][0])
        else:
            vm_refs = self.cs_si.get('service-instance', {}).get('virtual_machine_back_refs')
            vm_refs = [vm_ref['to'][0] for vm_ref in vm_refs]
        return (set(vm_refs), None)
    # end get_vm_refs

    @retry(delay=5, tries=10)
    def verify_svm(self, wait_for_vms=True):
        """check Service VM"""
        # Get the pt_refs in case of v2 and vm_refs in case of v1
        # From the pt_refs, get the vmi_refs and then get the VMs from vmi_refs
        # From svm_ids, get the svm_list
        # Verify the SVMs in the svm_list

        (vm_refs, msg) = self.get_vm_refs()

        if not vm_refs:
            errmsg = "SI %s does not have any Service VM" % self.si_name
            self.logger.warn(errmsg)
            return (False, errmsg)

        self.svm_ids = vm_refs
        self.logger.debug('The SVMs in the SI are : %s' %self.svm_list)

        if self.svc_template.service_template_properties.version == 1:
            if len(vm_refs) != self.max_inst:
                errmsg = ("SI %s does not have all Service VMs. Expected: %s"
                          ", Got : %s" % (self.si_name, self.max_inst, len(vm_refs)))
                self.logger.warn(errmsg)
                return (False, errmsg)

        # Populate the SVMs
        self.get_svms()
        for svm_id in self.svm_ids:
            cs_svm = self.api_s_inspect.get_cs_vm(vm_id=svm_id, refresh=True)
            if not cs_svm:
                errmsg = "Service VM for SI '%s' not launched" % self.si_name
                self.logger.warn(errmsg)
                return (False, errmsg)
        self.logger.debug("Service VM for SI '%s' is launched", self.si_name)
        if wait_for_vms:
            if self.service_mode != 'transparent':
                for vm in self.svm_list:
                    assert vm.wait_till_vm_is_up(), 'SVM is not up'
        self.vm_refs = vm_refs
        return True, None

    @retry(delay=1, tries=5)
    def verify_interface_props(self, svc_vm_if):
        """check if properties"""
        try:
            vm_if_props = svc_vm_if[
                'virtual-machine-interface']['virtual_machine_interface_properties']
        except KeyError:
            vm_if_props = None
        if not vm_if_props:
            errmsg = "No VM interface in Service VM of SI %s" % self.si_name
            self.logger.warn(errmsg)
            return (False, errmsg)
        self.logger.debug(
            "VM interface present in Service VM of SI %s", self.si_name)

        self.if_type = vm_if_props['service_interface_type']
        if (not self.if_type and self.if_type not in self.if_details.keys()):
            errmsg = "Interface type '%s' is not present in Servcice VM of SI '%s'" % (
                self.if_type, self.si_name)
            self.logger.warn(errmsg)
            return (False, errmsg)
        self.logger.debug(
            "Interface type '%s' is present in Service VM of SI '%s'", self.if_type, self.si_name)
        return True, None

    @retry(delay=1, tries=5)
    def verify_vn_links(self, svc_vm_if):
        """check vn links"""
        try:
            vn_refs = svc_vm_if[
                'virtual-machine-interface']['virtual_network_refs']
        except KeyError:
            vn_refs = None
        if not vn_refs:
            errmsg = "IF %s has no back refs to  vn" % self.if_type
            self.logger.warn(errmsg)
            return (False, errmsg)
        self.logger.debug("IF %s has back refs to  vn", self.if_type)
        for vn in vn_refs:
            self.svc_vn = self.api_s_inspect.get_cs_vn(
                # project=self.project.name, vn=vn['to'][-1], refresh=True)
                domain=vn['to'][0],project=vn['to'][1], vn=vn['to'][-1], refresh=True)
            if not self.svc_vn:
                errmsg = "IF %s has no vn" % self.if_type
                self.logger.warn(errmsg)
                return (False, errmsg)
            if self.svc_vn['virtual-network']['name'] in self.svn_list:
                self.cs_svc_vns.append(vn['to'][-1])
                self.logger.debug('SVC_VNs = %s' % self.cs_svc_vns)
            self.logger.debug("IF %s has vn '%s'", self.if_type,
                              self.svc_vn['virtual-network']['name'])
        return True, None

    @retry(delay=1, tries=5)
    def verify_ri(self, svc_vm_if):
        """check routing instance"""
        try:
            ri_refs = svc_vm_if[
                'virtual-machine-interface']['routing_instance_refs']
        except KeyError:
            ri_refs = None
        vn_name = self.svc_vn['virtual-network']['name']
        if not ri_refs:
            errmsg = "IF %s, VN %s has no back refs to routing instance" % (
                self.if_type, vn_name)
            self.logger.warn(errmsg)
            return (False, errmsg)
        self.logger.debug(
            "IF %s, VN %s has back refs to routing instance", self.if_type, vn_name)

        for ri in ri_refs:
            svc_ri = self.api_s_inspect.get_cs_ri_by_id(ri['uuid'])
            if not svc_ri:
                errmsg = "IF %s VN %s has no RI" % (self.if_type, vn_name)
                self.logger.warn(errmsg)
                return (False, errmsg)
            if svc_ri['routing-instance']['name'] in self.svn_list:
                self.cs_svc_ris.append(ri['uuid'])
            ri_name = svc_ri['routing-instance']['name']
            self.logger.debug("IF %s VN %s has RI", self.if_type, vn_name)
            if ri_name == vn_name:
                continue
            else:
                if not ri['attr']:
                    errmsg = "IF %s VN %s RI %s no attributes" % (
                        self.if_type, vn_name, ri_name)
                    self.logger.warn(errmsg)
                    return (False, errmsg)
                self.logger.debug("IF %s VN %s RI %s has attributes",
                                  self.if_type, vn_name, ri_name)
                # check service chain
                sc_info = svc_ri[
                    'routing-instance']['service_chain_information']
                if not sc_info:
                    errmsg = "IF %s VN %s RI %s has no SCINFO" % (
                        self.if_type, vn_name, ri_name)
                    self.logger.warn(errmsg)
                    return (False, errmsg)
                self.logger.debug("IF %s VN %s RI %s has SCINFO",
                                  self.if_type, vn_name, ri_name)
        return True, None

    @retry(delay=2, tries=10)
    def verify_svm_interface(self):
        # check VM interfaces
        pt = self.cs_si['service-instance'].get('port_tuples', None)
        if not pt:
            for svm_id in self.svm_ids:
                cs_svm = self.api_s_inspect.get_cs_vm(
                    vm_id=svm_id, refresh=True)
                svm_ifs = (cs_svm['virtual-machine'].get('virtual_machine_interfaces') or
                           cs_svm['virtual-machine'].get('virtual_machine_interface_back_refs'))

            if svm_ifs is None:
                errmsg = "Service VM hasn't come up."
                self.logger.warn(errmsg)
                return False, errmsg

            elif len(svm_ifs) != len(self.if_details):
                errmsg = ('Service VM does not have all the interfaces. Got %s,'
                         'Expected : %s' % (svm_ifs, self.if_details))
                self.logger.warn(errmsg)
                return False, errmsg

            svc_vm_ifs = self.api_s_inspect.get_cs_vmi_of_vm(
                svm_id, refresh=True)
            for svc_vm_if in svc_vm_ifs:
                result, msg = self.verify_interface_props(svc_vm_if)
                if not result:
                    return result, msg

                result, msg = self.verify_vn_links(svc_vm_if)
                if not result:
                    return result, msg

                result, msg = self.verify_ri(svc_vm_if)
                if not result:
                    return result, msg
        return True, None

    def verify_on_setup(self, report=True, wait_for_vms=True):
        if report:
            self.report(self.verify_si())
            self.report(self.verify_st())
            self.report(self.verify_svm(wait_for_vms))
            if self.svc_template.service_template_properties.version == 2:
                self.report(self.verify_pt())
            self.report(self.verify_svm_interface())
        else:
            # Need verifications to be run without asserting so that they can
            # retried to wait for instances to come up
            result = True
            msg = ""
            result1, msg1 = self.verify_si()
            if not result1:
                result = False
                msg = msg + msg1
            result1, msg1 = self.verify_st()
            if not result1:
                result = False
                msg = msg + msg1
            result1, msg1 = self.verify_svm()
            if not result1:
                result = False
                msg = msg + msg1
            else:
                # verification has dependency on verify_svm
                result1, msg1 = self.verify_svm_interface()
                if not result1:
                    result = False
                    msg = msg + msg1
            return result, msg

        return True, None
    # end verify_on_setup

    def report(self, result):
        if type(result) is tuple:
            result, errmsg = result
        if not result:
            assert False, errmsg

    @retry(delay=2, tries=15)
    def verify_si_not_in_api_server(self):
        if not self.si:
            return (True, None)
        si = self.api_s_inspect.get_cs_si(
            domain=self.domain_name, project=self.project.name, si=self.si_name, refresh=True)
        if si:
            errmsg = "Service instance %s not removed from api server" % self.si_name
            self.logger.warn(errmsg)
            return (False, errmsg)
        self.logger.debug("Service instance %s removed from api server" %
                          self.si_name)
        return (True, None)

    @retry(delay=5, tries=20)
    def verify_svm_not_in_api_server(self):
        '''
        SVM can still be present , but it should not be linked to the SI
        '''
        for svm_id in self.svm_ids:
            cs_svm = self.api_s_inspect.get_cs_vm(vm_id=svm_id, refresh=True)
            if cs_svm and cs_svm.service_instance_refs():
                errmsg = "Service VM %s still has ref for SI %s" % (
                            cs_svm.fq_name, cs_svm.service_instance_refs)
                self.logger.warn(errmsg)
                return (False, errmsg)
        self.logger.debug("All Service VMs unlinked from SI %s" % (self.si_name))
        return (True, None)

    def si_exists(self):
        svc_instances = self.vnc_lib.service_instances_list()[
            'service-instances']
        self.logger.debug("%s svc intances found in all projects. They are %s" % (
            len(svc_instances), svc_instances))
        # Filter SI's in current project as the above list call gives SIs in
        # all projects
        project_si_list = []
        for x in svc_instances:
            proj_of_x = [x['fq_name'][0], x['fq_name'][1]]
            if proj_of_x == self.project_fq_name:
                project_si_list.append(x)
        self.logger.debug("%s svc intances found in current project. They are %s" % (
            len(project_si_list), project_si_list))
        if (len(project_si_list) == 0 and len(svc_instances) == 0):
            return False
        else:
            return True

    @retry(delay=2, tries=35)
    def verify_svn_not_in_api_server(self):
        if self.si_exists():
            self.logger.info(
                "Some Service Instance exists; skip SVN check in API server")
            return (True, None)
        for vn in self.cs_svc_vns:
            svc_vn = self.api_s_inspect.get_cs_vn(
                domain=self.domain_name, project=self.project.name, vn=vn, refresh=True)
            self.logger.debug('Service VN %s seen' % svc_vn)
            # We will not worry about the Service-VNs not generated via
            # fixtures
            if (svc_vn and (svc_vn not in self.svn_list)):
                errmsg = "Service VN %s is not removed from api server" % vn
                self.logger.warn(errmsg)
                return (False, errmsg)
            self.logger.debug("Service VN %s is removed from api server", vn)
        return (True, None)

    @retry(delay=2, tries=15)
    def verify_ri_not_in_api_server(self):
        if self.si_exists():
            self.logger.debug(
                "Some Service Instance exists; skip RI check in API server")
            return (True, None)
        for ri in self.cs_svc_ris:
            svc_ri = self.api_s_inspect.get_cs_ri_by_id(ri)
            if svc_ri:
                errmsg = "RI %s is not removed from api server" % ri
                self.logger.warn(errmsg)
                return (False, errmsg)
            self.logger.debug("RI %s is removed from api server", ri)
        return (True, None)

    def verify_on_cleanup(self):
        result = True
        result, msg = self.verify_si_not_in_api_server()
        assert result, msg
        result, msg = self.verify_svm_not_in_api_server()
        assert result, msg
        if self.service_mode != 'in-network-nat':
            result, msg = self.verify_svn_not_in_api_server()
            assert result, msg
            result, msg = self.verify_ri_not_in_api_server()
            assert result, msg

        return result
    # end verify_on_cleanup

    def delete_port_tuple(self, port_tuples_uuid):
        pass


#    def add_port_tuple(self, svm, pt_name):
    def add_port_tuple(self, svm_pt_props={}):
        '''
            svm_pt_props : { 'manangement' : VMI uuid ,
                             'left' : VMI uuid , etc }
        '''
        if not svm_pt_props:
            return
        pt_name = svm_pt_props.get('name', get_random_name('port_tuple'))
        pt_obj = PortTuple(name=pt_name, parent_obj=self.si_obj)
        pt_uuid = self.vnc_lib.port_tuple_create(pt_obj)
        self.port_tuples_uuids.append(pt_uuid)
#        ports_list = []

        for intf_type, vmi_id in svm_pt_props.iteritems():
            if intf_type == 'name':
                continue
            vmi_obj = self.vnc_lib.virtual_machine_interface_read(id=vmi_id)
            vmi_props = vmi_obj.virtual_machine_interface_properties or \
                            VirtualMachineInterfacePropertiesType()
            vmi_props.set_service_interface_type(intf_type)
            vmi_obj.set_virtual_machine_interface_properties(vmi_props)
            vmi_obj.add_port_tuple(pt_obj)
            self.vnc_lib.virtual_machine_interface_update(vmi_obj)
    # end add_port_tuple

    def add_port_tuple_subIntf(self, mgmt_vmi_id, left_vmi_id, right_vmi_id, pt_name):
        pt_obj = PortTuple(name=pt_name, parent_obj=self.si_obj)
        pt_uuid = self.vnc_lib.port_tuple_create(pt_obj)
        ports_list = []
        ports_list.append(mgmt_vmi_id)
        ports_list.append(left_vmi_id)
        ports_list.append(right_vmi_id)
        intf_type = ['management', 'left', 'right']
        for index in range(0, len(ports_list)):
            port_id = ports_list[index]
            vmi_obj = self.vnc_lib.virtual_machine_interface_read(id=port_id)
            vmi_props = vmi_obj.virtual_machine_interface_properties or \
                            VirtualMachineInterfacePropertiesType()
            vmi_props.set_service_interface_type(intf_type[index])
            vmi_obj.set_virtual_machine_interface_properties(vmi_props)
            vmi_obj.add_port_tuple(pt_obj)
            self.vnc_lib.virtual_machine_interface_update(vmi_obj)
    # end add_port_tuple


# end SvcInstanceFixture
