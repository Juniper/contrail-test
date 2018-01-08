from vnc_api.vnc_api import *
import vnc_api_test
from tcutils.util import *

class SLOFixture(vnc_api_test.VncLibFixture):
    '''
    Security Logging Object Fixture
    '''

    def __init__(self, parent_obj, **kwargs):
        '''
        Optional param:
            sg_refs: list of dict of SG objects and ref_data of SecurityLoggingObjectRuleListType object
                [{'obj':<SG obj>, 'ref_data':<ref data obj>}]
            vn_policy_refs: same as sg_refs but for VN policy
        '''
        super(SLOFixture, self).__init__(self, **kwargs)
        self.parent_obj = parent_obj
        self.name = None
        self.uuid = None
        self.obj = None
        self.rate = None
        self.sg_refs = None
        self.vn_policy_refs = None
        self.parse_slo_kwargs(**kwargs)
        self.already_present = None

        if self.parent_obj is None:
            fq_name = [ 'default-global-system-config',
                        'default-global-vrouter-config']
            self.parent_obj = self.vnc_lib.global_vrouter_config_read(fq_name=fq_name)

    def parse_slo_kwargs(self, **kwargs):
        self.sg_refs = kwargs.get('sg_refs',
            self.sg_refs)
        self.vn_policy_refs = kwargs.get('vn_policy_refs',
            self.vn_policy_refs)
        self.rate = kwargs.get('rate',
            self.rate)
        self.name = kwargs.get('name',
            self.name)
        self.uuid = kwargs.get('uuid',
            self.uuid)

    def _populate_attr(self):
        if self.obj:
            self.name = self.obj.name
            self.uuid = self.obj.uuid
            self.fq_name_str = self.obj.get_fq_name_str()

    def read(self):
        if self.uuid:
            self.obj = self.read_slo(self.uuid)
            if not self.obj:
                raise Exception('SLO with id %s not found' % (
                    self.uuid))
            self._populate_attr()
            return self.obj

        return False

    def setUp(self):
        super(SLOFixture, self).setUp()
        self.api_s_inspects = self.connections.api_server_inspects
        self.agent_inspect = self.connections.agent_inspect
        self.vnc_lib_fixture = self.connections.vnc_lib_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.vnc_h = self.vnc_lib_fixture.vnc_h
        self.project_name = self.connections.project_name
        self.project_id = self.connections.project_id
        self.name = self.name or get_random_name('slo_' + self.project_name)

        self.create()

    def cleanUp(self):
        super(SLOFixture, self).cleanUp()
        self.delete()

    def create(self):
        if self.read():
            self.already_present = True
            self.logger.debug("SLO %s already present,"
                "not creating it" % (self.name))
            return

        if self.obj:
            self._populate_attr()
            self.already_present = True
            self.logger.debug("SLO %s already present,"
                "not creating it" % (self.name))
        else:
            self.create_slo()
            self.already_present = False


    def delete(self, verify=True):
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            self.delete_slo(self.uuid)
            self.verify_cleared_from_setup(verify=verify)
        else:
            self.logger.info('Skipping the deletion of SLO %s' %
                             (self.name))

    def create_slo(self):
        '''
            Creates a Security Logging Object
        '''
        if self.rate is not None:
            self.obj = SecurityLoggingObject(name=self.name,
                parent_obj=self.parent_obj,
                security_logging_object_rate=self.rate)
        else:
            #Default SLO rate
            self.obj = SecurityLoggingObject(name=self.name,
                parent_obj=self.parent_obj)

        if self.sg_refs:
            for sg_ref in self.sg_refs:
                self.obj.add_security_group(sg_ref['obj'], sg_ref['ref_data'])
        if self.vn_policy_refs:
            for vn_policy_ref in self.vn_policy_refs:
                self.obj.add_network_policy(vn_policy_ref['obj'],
                    vn_policy_ref['ref_data'])

        self.uuid = self.vnc_lib.security_logging_object_create(self.obj)

        self.logger.info('Created SLO %s, UUID: %s' % (
                         self.vnc_lib.id_to_fq_name(self.uuid), self.uuid))
        self._populate_attr()

        return self.obj

    def delete_slo(self, uuid=None):
        '''
        Delete SLO

        Args:
            uuid : UUID of SLO
        '''
        uuid = uuid or self.uuid
        self.vnc_lib.security_logging_object_delete(id=uuid)
        self.logger.info('Deleted SLO %s' % (uuid))

    def read_slo(self, uuid=None):
        '''
        Read SLO

        Args:
            uuid : UUID of SLO
        '''
        uuid = uuid or self.uuid
        slo_obj = self.vnc_lib.security_logging_object_read(id=uuid)
        self.logger.info('SLO %s info %s' % (uuid,slo_obj))

        return slo_obj

    def verify_on_setup(self):
        result = True
        if not self.verify_slo_in_api_server():
            result = result and False
            self.logger.error(
                "One or more verifications in API Server for SLO "
                "%s failed" % (self.name))
            return result

        self.verify_is_run = True
        self.verify_result = result
        return result

    @retry(delay=2, tries=5)
    def verify_slo_in_api_server(self):
        ''' Verifies SLO in API Server.
        '''
        self.api_verification_flag = True
        cfgm_ip = self.inputs.cfgm_ips[0]

        self.api_s_slo_obj = self.api_s_inspects[cfgm_ip].get_cs_slo(
            slo_uuid=self.uuid)

        if not self.api_s_slo_obj:
            self.logger.warn("SLO %s is not found in API-Server" %
                             (self.uuid))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        if self.api_s_slo_obj['security-logging-object']['name'] != self.name:
            self.logger.warn(
                "SLO name %s in API-Server is not what was created" % (
                self.name))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        if self.api_s_slo_obj['security-logging-object'][
                'security_logging_object_rate'] != self.rate:
            self.logger.warn(
                "SLO rate %s in API-Server is not what was created" % (
                self.rate))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        self.logger.debug("Verifications for SLO %s in API server passed" %
            (self.name))
        return True

    @retry(delay=2, tries=5)
    def verify_slo_not_in_api(self):
        cfgm_ip = self.inputs.cfgm_ips[0]
        self.api_s_slo_obj = self.api_s_inspects[cfgm_ip].get_cs_slo(
            slo_uuid=self.uuid)

        if self.api_s_slo_obj:
            self.logger.warn("SLO %s is still seen in API server %s" % (
                self.name, cfgm_ip))
            return False
        self.logger.info("SLO %s is removed from API server %s" % (
            self.name, cfgm_ip))

        return True

    def verify_cleared_from_setup(self, verify=True):
        '''
            Verify that SLO is deleted from the setup
        '''
        if verify:
            assert self.verify_slo_not_in_api(), ("SLO cleanup verification "
                                                     "failed in api")

