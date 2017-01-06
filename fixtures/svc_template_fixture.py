import fixtures
from vnc_api.vnc_api import *
from tcutils.util import retry
try:
    from webui_test import *
except ImportError:
    pass


class SvcTemplateFixture(fixtures.Fixture):
    '''

    if_details : dict of dicts

        Ex : If v1 : {'management' : { 'shared_ip_enable' : True,
                                       'static_route_enable' : False
                                    }
                      {'left': .... },
                      {'right': ... } ]
            If v2 : { 'management': {}, 'left': {}, 'right': {} }
    '''

    def __init__(self, connections,
                 st_name,
                 service_type,
                 if_details,
                 version=2,
                 service_mode='transparent',
                 flavor='contrail_flavor_2cpu',
                 availability_zone_enable = False,
                 svc_img_name=None,
                 svc_scaling=None):
        self.orch = connections.orch
        self.vnc_lib_h = connections.vnc_lib
        self.domain_name = connections.domain_name
        self.st_name = st_name
        self.st_obj = None
        self.uuid = None
        self.domain_fq_name = [self.domain_name]
        self.st_fq_name = [self.domain_name, self.st_name]
        self.image_name = svc_img_name
        self.service_type = service_type
        self.version = version
        self.if_details = if_details
        self.service_mode = service_mode
        self.svc_scaling = svc_scaling
        self.inputs = connections.inputs
        self.logger = self.inputs.logger
        self.connections = connections
        self.availability_zone_enable = None
        self.flavor = None
        if version == 1:
            if self.image_name:
                self.orch.get_image(self.image_name)
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
            domain = self.connections.vnc_lib_fixture.domain_read(fq_name=self.domain_fq_name)
            svc_template = ServiceTemplate(
                name=self.st_name, parent_obj=domain)
            svc_properties = ServiceTemplateType()
            svc_properties.set_service_type(self.service_type)
            svc_properties.set_service_mode(self.service_mode)
            svc_properties.set_version(self.version)
            # Add flavor if not already added
            if self.version == 1:
                svc_properties.set_image_name(self.image_name)
                svc_properties.set_service_scaling(self.svc_scaling)
                self.orch.get_flavor(self.flavor)
                svc_properties.set_flavor(self.flavor)
                svc_properties.set_availability_zone_enable(self.availability_zone_enable)
#            for itf in self.if_list:
            for itf_type, val in self.if_details.iteritems():
                shared_ip = val.get('shared_ip_enable', None)
                static_route_enable = val.get('static_route_enable', None)
                if_type = ServiceTemplateInterfaceType(
                    service_interface_type=itf_type,
                    shared_ip=shared_ip,
                    static_route_enable=static_route_enable)
                if_type.set_service_interface_type(itf_type)
                svc_properties.add_interface_type(if_type)

            svc_template.set_service_template_properties(svc_properties)
            if self.inputs.is_gui_based_config():
                self.webui.create_svc_template(self)
            else:
                self.uuid = self.vnc_lib_h.service_template_create(svc_template)
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
