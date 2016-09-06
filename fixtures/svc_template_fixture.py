import fixtures
from vnc_api.vnc_api import *
from tcutils.util import retry
try:
    from webui_test import *
except ImportError:
    pass


class SvcTemplateFixture(fixtures.Fixture):

    def __init__(self, connections, inputs, domain_name, st_name, svc_img_name,
                 svc_type, if_list, svc_scaling, ordered_interfaces, version=1, svc_mode='transparent', flavor='contrail_flavor_2cpu',
                 availability_zone_enable = False):
        self.orch = connections.orch
        self.vnc_lib_h = connections.vnc_lib
        self.domain_name = domain_name
        self.st_name = st_name
        self.st_obj = None
        self.domain_fq_name = [self.domain_name]
        self.st_fq_name = [self.domain_name, self.st_name]
        self.image_name = svc_img_name
        if self.image_name:
            self.orch.get_image(self.image_name)
        self.svc_type = svc_type
        self.version = version
        self.if_list = if_list
        self.svc_mode = svc_mode
        self.svc_scaling = svc_scaling
        self.ordered_interfaces = ordered_interfaces
        self.logger = inputs.logger
        self.inputs = inputs
        self.connections = connections
        self.flavor = self.orch.get_default_image_flavor(self.image_name)
        if self.inputs.availability_zone:
            availability_zone_enable = True
        self.availability_zone_enable = availability_zone_enable
        if self.inputs.verify_thru_gui():
            self.browser = connections.browser
            self.browser_openstack = connections.browser_openstack
            self.webui = WebuiTest(connections, inputs)
    # end __init__

    def setUp(self):
        super(SvcTemplateFixture, self).setUp()
        self.st_obj = self._create_st()
    # end setUp

    def cleanUp(self):
        super(SvcTemplateFixture, self).cleanUp()
        if self.inputs.is_gui_based_config():
            self.webui.delete_svc_template(self)
        else:
            self._delete_st()
        assert self.verify_on_cleanup()
    # end cleanUp

    def _create_st(self):
        self.logger.debug("Creating service template: %s", self.st_fq_name)
        try:
            svc_template = self.vnc_lib_h.service_template_read(
                fq_name=self.st_fq_name)
            self.logger.debug(
                "Service template: %s already exists", self.st_fq_name)
        except NoIdError:
            domain = self.vnc_lib_h.domain_read(fq_name=self.domain_fq_name)
            svc_template = ServiceTemplate(
                name=self.st_name, parent_obj=domain)
            svc_properties = ServiceTemplateType()
            svc_properties.set_image_name(self.image_name)
            svc_properties.set_service_type(self.svc_type)
            svc_properties.set_service_mode(self.svc_mode)
            svc_properties.set_version(self.version)
            svc_properties.set_service_scaling(self.svc_scaling)
            # Add flavor if not already added
            self.orch.get_flavor(self.flavor)
            svc_properties.set_flavor(self.flavor)
            svc_properties.set_ordered_interfaces(self.ordered_interfaces)
            svc_properties.set_availability_zone_enable(self.availability_zone_enable)
            for itf in self.if_list:
                if_type = ServiceTemplateInterfaceType(
                    service_interface_type=itf[0], shared_ip=itf[1], static_route_enable=itf[2])
                if_type.set_service_interface_type(itf[0])
                svc_properties.add_interface_type(if_type)

            svc_template.set_service_template_properties(svc_properties)
            if self.inputs.is_gui_based_config():
                self.webui.create_svc_template(self)
            else:
                self.vnc_lib_h.service_template_create(svc_template)
            svc_template = self.vnc_lib_h.service_template_read(
                fq_name=self.st_fq_name)

        return svc_template
    # end _create_st

    def _delete_st(self):
        self.logger.debug("Deleting service template: %s", self.st_fq_name)
        self.vnc_lib_h.service_template_delete(fq_name=self.st_fq_name)
    # end _delete_st

    def verify_on_setup(self):
        result = True
        try:
            svc_template = self.vnc_lib_h.service_template_read(
                fq_name=self.st_fq_name)
            self.logger.debug(
                "Service template: %s created succesfully", self.st_fq_name)
        except NoIdError:
            self.logger.error("Service template: %s not created." %
                              self.st_fq_name)
            result = result and False
            return False
        assert self.version == svc_template.service_template_properties.version, "Svc template version mismatch"
        return result
    # end verify_on_setup

    @retry(delay=5, tries=6)
    def verify_on_cleanup(self):
        result = True
        try:
            svc_template = self.vnc_lib_h.service_instance_read(
                fq_name=self.st_fq_name)
            self.logger.debug(
                "Service template: %s still not removed", self.st_fq_name)
            result = result and False
            return False
        except NoIdError:
            self.logger.info("Service template: %s deleted successfully." %
                             self.st_fq_name)
        return result
    # end verify_on_cleanup

# end SvcTemplateFixture
