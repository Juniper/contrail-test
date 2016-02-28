import fixtures
from vnc_api.vnc_api import *
from tcutils.util import retry
from time import sleep
from tcutils.services import get_status
try:
    from webui_test import *
except ImportError:
    pass


class SvcInstanceFixture(fixtures.Fixture):

    def __init__(self, connections, inputs, domain_name, project_name, si_name,
                 svc_template, if_list, left_vn_name=None, right_vn_name=None, do_verify=True, max_inst=1, static_route=['None', 'None', 'None']):
        self.vnc_lib = connections.vnc_lib
        self.api_s_inspect = connections.api_server_inspect
        self.nova_h = connections.nova_h
        self.inputs = connections.inputs
        self.domain_name = domain_name
        self.project_name = project_name
        self.si_name = si_name
        self.svc_template = svc_template
        self.st_name = svc_template.name
        self.si_obj = None
        self.domain_fq_name = [self.domain_name]
        self.project_fq_name = [self.domain_name, self.project_name]
        self.si_fq_name = [self.domain_name, self.project_name, self.si_name]
        self.logger = inputs.logger
        self.left_vn_name = left_vn_name
        self.right_vn_name = right_vn_name
        self.already_present = False
        self.do_verify = do_verify
        self.if_list = if_list
        self.max_inst = max_inst
        self.static_route = static_route
        self.si = None
        self.svm_ids = []
        self.cs_svc_vns = []
        self.cs_svc_ris = []
        self.svn_list = ['svc-vn-mgmt', 'svc-vn-left', 'svc-vn-right']
        if self.inputs.verify_thru_gui():
            self.browser = connections.browser
            self.browser_openstack = connections.browser_openstack
            self.webui = WebuiTest(connections, inputs)
    # end __init__

    def setUp(self):
        super(SvcInstanceFixture, self).setUp()
        self.si_obj = self._create_si()
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
        self.logger.debug("Creating service instance: %s", self.si_fq_name)
        try:
            svc_instance = self.vnc_lib.service_instance_read(
                fq_name=self.si_fq_name)
            self.already_present = True
            self.logger.debug(
                "Service instance: %s already exists", self.si_fq_name)
        except NoIdError:
            project = self.vnc_lib.project_read(fq_name=self.project_fq_name)
            svc_instance = ServiceInstance(self.si_name, parent_obj=project)
            if self.left_vn_name and self.right_vn_name:
                si_prop = ServiceInstanceType(
                    left_virtual_network=self.left_vn_name,
                    right_virtual_network=self.right_vn_name)
                bridge = False
                if 'bridge_svc_instance_1' in self.si_fq_name:
                    bridge = True
                for itf in self.if_list:
                    if (itf[0] == 'left' and not bridge):
                        virtual_network = self.left_vn_name
                    elif (itf[0] == 'right' and not bridge):
                        virtual_network = self.right_vn_name
                    else:
                        virtual_network = ""
                    if_type = ServiceInstanceInterfaceType(
                        virtual_network=virtual_network,
                        static_routes=RouteTableType([RouteType(prefix=self.static_route[self.if_list.index(itf)])]))
                    if_type.set_static_routes(
                        RouteTableType([RouteType(prefix=self.static_route[self.if_list.index(itf)])]))
                    si_prop.add_interface_list(if_type)

            else:
                if self.left_vn_name:
                    # In Network mode
                    si_prop = ServiceInstanceType(
                        left_virtual_network=self.left_vn_name)
                    intf_count = 1
                    virtual_network = self.left_vn_name
                else:
                    # Transparent mode
                    si_prop = ServiceInstanceType()
                    intf_count = 1
                    virtual_network = ""
                    if self.svc_template.service_template_properties.service_type == 'firewall':
                        # Transparent mode firewall
                        intf_count = 3
                for i in range(intf_count):
                    if_type = ServiceInstanceInterfaceType(
                        virtual_network=virtual_network)
                    si_prop.add_interface_list(if_type)
            si_prop.set_scale_out(ServiceScaleOutType(self.max_inst))
            svc_instance.set_service_instance_properties(si_prop)
            svc_instance.set_service_template(self.svc_template)
            if self.inputs.is_gui_based_config():
                self.webui.create_svc_instance(self)
            else:
                self.vnc_lib.service_instance_create(svc_instance)
            svc_instance = self.vnc_lib.service_instance_read(
                fq_name=self.si_fq_name)
        return svc_instance
    # end _create_si

    def _delete_si(self):
        self.logger.debug("Deleting service instance: %s", self.si_fq_name)
        self.vnc_lib.service_instance_delete(fq_name=self.si_fq_name)
    # end _delete_si

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

    def verify_st(self):
        """check service template"""
        self.cs_si = self.api_s_inspect.get_cs_si(
            project=self.project.name, si=self.si_name, refresh=True)
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
    def verify_svm(self):
        """check Service VM"""
        # read again from api in case of retry
        self.cs_si = self.api_s_inspect.get_cs_si(
            project=self.project.name, si=self.si_name, refresh=True)
        try:
            self.vm_refs = self.cs_si[
                'service-instance']['virtual_machine_back_refs']
        except KeyError:
            self.vm_refs = None
        if not self.vm_refs:
            errmsg = "SI %s does not have back refs to Service VM" % self.si_name
            self.logger.warn(errmsg)
            return (False, errmsg)

        self.logger.debug("SI %s has back refs to Service VM", self.si_name)
        self.svm_ids = [vm_ref['to'][0] for vm_ref in self.vm_refs]
        for svm_id in self.svm_ids:
            cs_svm = self.api_s_inspect.get_cs_vm(vm_id=svm_id, refresh=True)
            if not cs_svm:
                errmsg = "Service VM for SI '%s' not launched" % self.si_name
                self.logger.warn(errmsg)
                #self.logger.debug("Service monitor status: %s", get_status('contrail-svc-monitor'))
                return (False, errmsg)
        self.logger.debug("Serivce VM for SI '%s' is launched", self.si_name)
        return True, None

    def svm_compute_node_ip(self):
        admin_project_uuid = self.api_s_inspect.get_cs_project(project=self.project.name)['project'][
            'uuid']
        #svm_name = self.si_name + str('_1')
        #svm_name = self.si_obj.uuid + str('__1')
        svm_name = self.si_obj.name + str('__1')
        # handle change in <si_name> to <domain>__<project>__<si_name>
        svm_name = self.inputs.domain_name + '__' + \
            self.inputs.project_name + '__' + svm_name
        svm_obj = self.nova_h.get_vm_if_present(
            svm_name, admin_project_uuid)
        svm_compute_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(svm_obj)]['host_ip']
        return svm_compute_node_ip

    @retry(delay=1, tries=5)
    def verify_interface_props(self):
        """check if properties"""
        try:
            vm_if_props = self.svc_vm_if[
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
        if (not self.if_type and self.if_type not in self.if_list):
            errmsg = "Interface type '%s' is not present in Servcice VM of SI '%s'" % (
                self.if_type, self.si_name)
            self.logger.warn(errmsg)
            return (False, errmsg)
        self.logger.debug(
            "Interface type '%s' is present in Service VM of SI '%s'", self.if_type, self.si_name)
        return True, None

    @retry(delay=1, tries=5)
    def verify_vn_links(self):
        """check vn links"""
        try:
            vn_refs = self.svc_vm_if[
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
        #        project=self.project.name, vn=vn['to'][-1], refresh=True)
                project=vn['to'][1], vn=vn['to'][-1], refresh=True)
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
    def verify_ri(self):
        """check routing instance"""
        try:
            ri_refs = self.svc_vm_if[
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
        for svm_id in self.svm_ids:
            cs_svm = self.api_s_inspect.get_cs_vm(vm_id=svm_id, refresh=True)
            svm_ifs = (cs_svm['virtual-machine'].get('virtual_machine_interfaces') or
                       cs_svm['virtual-machine'].get('virtual_machine_interface_back_refs'))

        if svm_ifs is None:
            errmsg = "Service VM hasn't come up."
            self.logger.warn(errmsg)
            return False, errmsg

        elif len(svm_ifs) != len(self.if_list):
            errmsg = "Service VM dosen't have all the interfaces %s" % self.if_list
            self.logger.warn(errmsg)
            return False, errmsg

        svc_vm_if = self.api_s_inspect.get_cs_vmi_of_vm(svm_id, refresh=True)
        for self.svc_vm_if in svc_vm_if:
            result, msg = self.verify_interface_props()
            if not result:
                return result, msg

            result, msg = self.verify_vn_links()
            if not result:
                return result, msg

            result, msg = self.verify_ri()
            if not result:
                return result, msg
        return True, None

    def verify_on_setup(self, report=True):
        if report:
            self.report(self.verify_si())
            self.report(self.verify_st())
            self.report(self.verify_svm())
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
            project=self.project.name, si=self.si_name, refresh=True)
        if si:
            errmsg = "Service instance %s not removed from api server" % self.si_name
            self.logger.warn(errmsg)
            return (False, errmsg)
        self.logger.debug("Service instance %s removed from api server" %
                          self.si_name)
        return (True, None)

    @retry(delay=5, tries=20)
    def verify_svm_not_in_api_server(self):
        for svm_id in self.svm_ids:
            cs_svm = self.api_s_inspect.get_cs_vm(vm_id=svm_id, refresh=True)
            if cs_svm:
                errmsg = "Service VM for SI '%s' not deleted" % self.si_name
                self.logger.warn(errmsg)
                return (False, errmsg)
        self.logger.debug("Serivce VM for SI '%s' is deleted", self.si_name)
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

    @retry(delay=2, tries=30)
    def verify_svn_not_in_api_server(self):
        if self.si_exists():
            self.logger.info(
                "Some Service Instance exists; skip SVN check in API server")
            return (True, None)
        for vn in self.cs_svc_vns:
            svc_vn = self.api_s_inspect.get_cs_vn(
                project=self.project.name, vn=vn, refresh=True)
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
        if self.do_verify:
            result, msg = self.verify_svn_not_in_api_server()
            assert result, msg
            result, msg = self.verify_ri_not_in_api_server()
            assert result, msg

        return result
    # end verify_on_cleanup

# end SvcInstanceFixture
