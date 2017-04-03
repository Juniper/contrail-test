from tcutils.util import *
from vnc_api.vnc_api import *
import vnc_api_test

class BDFixture(vnc_api_test.VncLibFixture):
    '''
    Bridge Domain Fixture
    '''

    def __init__(self, parent_obj, bd_name=None, bd_uuid=None, **kwargs):
        super(BDFixture, self).__init__(self, **kwargs)
        self.parent_obj = parent_obj
        self.bd_name = bd_name
        self.bd_uuid = bd_uuid
        self.bd_obj = None
        self.mac_learning_enabled = None
        self.mac_limit_control = None
        self.mac_move_control = None
        self.mac_aging_time = None
        self.isid = None
        self.parse_bd_kwargs(**kwargs)
        self.already_present = None

    def parse_bd_kwargs(self, **kwargs):
        self.mac_learning_enabled = kwargs.get('mac_learning_enabled',
            self.mac_learning_enabled)
        self.mac_limit_control = kwargs.get('mac_limit_control',
            self.mac_limit_control)
        self.mac_move_control = kwargs.get('mac_move_control',
            self.mac_move_control)
        self.mac_aging_time = kwargs.get('mac_aging_time',
            self.mac_aging_time)
        self.isid = kwargs.get('isid', self.isid)

    def _populate_attr(self):
        if self.bd_obj:
            self.bd_name = self.bd_obj.name
            self.mac_learning_enabled = self.bd_obj.mac_learning_enabled
            self.mac_limit_control = self.bd_obj.mac_limit_control
            self.mac_move_control = self.bd_obj.mac_move_control
            self.mac_aging_time = self.bd_obj.mac_aging_time
            self.isid = self.bd_obj.isid
            self.bd_uuid = self.bd_obj.uuid
            self.fq_name_str = self.bd_obj.get_fq_name_str()

    def read(self):
        if self.bd_uuid:
            self.bd_obj = self.read_bd(self.bd_uuid)
            if not self.bd_obj:
                raise Exception('Bridge Domain with id %s not found' % (
                    self.bd_uuid))
            self._populate_attr()
            return self.bd_obj

        return False

    def setUp(self):
        super(BDFixture, self).setUp()
        self.api_s_inspects = self.connections.api_server_inspects
        self.agent_inspect = self.connections.agent_inspect
        self.vnc_lib_fixture = self.connections.vnc_lib_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.vnc_h = self.vnc_lib_fixture.vnc_h
        self.project_name = self.connections.project_name
        self.project_id = self.connections.project_id
        self.bd_name = self.bd_name or get_random_name('bd_' + self.project_name)

        self.create()

    def cleanUp(self):
        super(BDFixture, self).cleanUp()
        self.delete()

    def create(self):
        if self.read():
            self.already_present = True
            self.logger.debug("Bridge Domain %s already present,"
                "not creating it" % (self.bd_name))
            return

        if self.bd_obj:
            self._populate_attr()
            self.already_present = True
            self.logger.debug("Bridge Domain %s already present,"
                "not creating it" % (self.bd_name))
        else:
            self.create_bd()
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
            self.delete_bd(self.bd_uuid)
            self.verify_cleared_from_setup(verify=verify)
        else:
            self.logger.info('Skipping the deletion of Bridge Domain %s' %
                             (self.bd_name))

    def create_bd(self):
        '''
            Creates a bridge domain
        '''
        self.bd_obj = BridgeDomain(name=self.bd_name,
                              parent_obj=self.parent_obj,
                              mac_learning_enabled=self.mac_learning_enabled,
                              mac_limit_control=self.mac_limit_control,
                              mac_move_control=self.mac_move_control,
                              mac_aging_time=self.mac_aging_time,
                              isid=self.isid)
        self.bd_uuid = self.vnc_lib.bridge_domain_create(self.bd_obj)
        self.logger.info('Created Bridge Domain %s, UUID: %s' % (
                         self.vnc_lib.id_to_fq_name(self.bd_uuid), self.bd_uuid))
        self._populate_attr()

        return self.bd_obj
    # end create_bd

    def delete_bd(self, uuid=None):
        '''
        Delete Bridge Domain object

        Args:
            uuid : UUID of BridgeDomain object
        '''
        uuid = uuid or self.bd_uuid
        self.vnc_lib.bridge_domain_delete(id=uuid)
        self.logger.info('Deleted Bridge Domain %s' % (uuid))
    # end delete_bd

    def read_bd(self, uuid=None):
        '''
        Read Bridge Domain object

        Args:
            uuid : UUID of BridgeDomain object
        '''
        uuid = uuid or self.bd_uuid
        bd_obj = self.vnc_lib.bridge_domain_read(id=uuid)
        self.logger.info('Bridge Domain %s info %s' % (uuid,bd_obj))

        return bd_obj
    # end read_bd

    def update_bd(self, **kwargs):
        '''
            Updates bridge domain
        '''
        self.parse_bd_kwargs(**kwargs)
        self.vnc_h.update_bd(uuid=self.bd_uuid, **kwargs)

    def add_bd_to_vmi(self, vmi_id, vlan_tag, verify=True):
        result = True
        bd_id = self.bd_uuid
        self.vnc_h.add_bd_to_vmi(bd_id, vmi_id, vlan_tag)

        if verify:
            result = self.verify_bd_for_vmi_in_computes(vmi_uuid=vmi_id)
            result = result and self.verify_bd_for_vn_in_agent(vmi_uuid=vmi_id)

        return result

    def verify_on_setup(self):
        result = True
        if not self.verify_bd_in_api_server():
            result = result and False
            self.logger.error(
                "One or more verifications in API Server for Bridge Domain "
                "%s failed" % (self.bd_name))
            return result

        self.verify_is_run = True
        self.verify_result = result
        return result
    # end verify_on_setup


    @retry(delay=2, tries=5)
    def verify_bd_in_api_server(self):
        """ Checks for Bridge Domain in API Server.
        """
        self.api_verification_flag = True
        cfgm_ip = self.inputs.cfgm_ips[0]

        self.api_s_bd_obj = self.api_s_inspects[cfgm_ip].get_cs_bridge_domain(
            bd_name=self.bd_name, refresh=True)

        if not self.api_s_bd_obj:
            self.logger.warn("Bridge Domain %s is not found in API-Server" %
                             (self.bd_name))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        if self.api_s_bd_obj['bridge-domain']['uuid'] != self.bd_uuid:
            self.logger.warn(
                "BD Object ID %s in API-Server is not what was created" % (
                self.bd_uuid))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        if self.api_s_bd_obj['bridge-domain']['parent_type'] != 'virtual-network' or \
            self.api_s_bd_obj['bridge-domain']['parent_uuid'] != self.parent_obj.uuid:
            self.logger.warn(
                "BD parent type %s and ID %s in API-Server is not as expected: %s" % (
                self.api_s_bd_obj['bridge-domain']['parent_type'],
                self.api_s_bd_obj['bridge-domain']['parent_uuid'],
                self.parent_obj.uuid))
            self.api_verification_flag = self.api_verification_flag and False

            return False
        if self.mac_learning_enabled and (
            self.api_s_bd_obj['bridge-domain']['mac_learning_enabled'] !=
                self.mac_learning_enabled):
            self.logger.warn("BD mac_learning_enabled %s in API-Server is "
                "not what was created %s" % (
                self.api_s_bd_obj['bridge-domain']['mac_learning_enabled'],
                self.mac_learning_enabled))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        if self.mac_limit_control and (
            (self.api_s_bd_obj['bridge-domain']['mac_limit_control']
                ['mac_limit'] != self.mac_limit_control.mac_limit) or (
            self.api_s_bd_obj['bridge-domain']['mac_limit_control']
                ['mac_limit_action'] != self.mac_limit_control.mac_limit_action)):
            self.logger.warn("BD mac_limit_control %s in API-Server is "
                "not what was created %s" % (
                self.api_s_bd_obj['bridge-domain']['mac_limit_control'],
                self.mac_limit_control))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        if self.mac_move_control and (
            (self.api_s_bd_obj['bridge-domain']['mac_move_control']
                ['mac_move_limit'] != self.mac_move_control.mac_move_limit
            ) or (
            self.api_s_bd_obj['bridge-domain']['mac_move_control']
                ['mac_move_limit_action'] !=
                self.mac_move_control.mac_move_limit_action) or (
            self.api_s_bd_obj['bridge-domain']['mac_move_control']
                ['mac_move_time_window'] !=
                self.mac_move_control.mac_move_time_window)):
            self.logger.warn("BD mac_move_control %s in API-Server is "
                "not what was created %s" % (
                self.api_s_bd_obj['bridge-domain']['mac_move_control'],
                self.mac_move_control))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        if self.mac_aging_time and (self.api_s_bd_obj['bridge-domain']
                ['mac_aging_time'] != self.mac_aging_time):
            self.logger.warn("BD mac_aging_time %s in API-Server is "
                "not what was created %s" % (
                self.api_s_bd_obj['bridge-domain']['mac_aging_time'],
                self.mac_aging_time))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        if self.isid and (self.api_s_bd_obj['bridge-domain']['isid'] !=
            self.isid):
            self.logger.warn("BD isid %s in API-Server is "
                "not what was created %s" % (
                self.api_s_bd_obj['bridge-domain']['isid'],
                self.isid))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        self.logger.info("Verifications in API Server %s for BD %s passed" %(
            cfgm_ip, self.bd_name))
        return True
    # end verify_bd_in_api_server


    @retry(delay=2, tries=2)
    def verify_bd_for_vn_in_agent(self, vmi_uuid):
        """
        Verify Bridge Domain for VN info in agent
        """
        vn_obj = self.parent_obj

        vmi_host = self.vnc_h.get_vmi_host_name(vmi_uuid)
        if not vmi_host:
            self.logger.error("VMI %s host could not be found from VNC API" % (
                vmi_uuid))
            return False
        vmi_host_ip = self.inputs.compute_info[vmi_host]

        bd_in_agent = self.agent_inspect[vmi_host_ip].get_bd(self.bd_uuid)
        if not bd_in_agent:
            self.logger.warn("Bridge Domain %s is not found in Agent %s" % (
                self.bd_name, vmi_host_ip))
            return False
        #Verify expected values in agent
        for bd in bd_in_agent:
            if bd['vn'] != vn_obj.uuid:
                self.logger.warn("VN uuid mismatch for Bridge Domain"
                    " in agent, actual: %s, expected: %s" % (
                    bd['vn'], vn_obj.uuid))
                result = False
                return result

            if bd['uuid'] != self.bd_uuid:
                self.logger.warn("BD uuid mismatch in agent"
                    ", actual: %s, expected: %s" % (
                    bd['uuid'], self.bd_uuid))
                result = False
                return result

            if int(bd['isid']) != self.isid:
                self.logger.warn("isid mismatch for Bridge Domain"
                    " in agent, actual: %s, expected: %s" % (
                    bd['isid'], self.isid))
                result = False
                return result

            if bd['pbb_etree_enabled'] != str(vn_obj.pbb_etree_enable):
                self.logger.warn("pbb_etree_enable value mismatch for Bridge Domain"
                    " in agent, actual: %s, expected: %s" % (
                    bd['pbb_etree_enabled'], str(vn_obj.pbb_etree_enable)))
                result = False
                return result

            if bool(bd['learning_enabled']) != self.mac_learning_enabled:
                self.logger.warn("mac_learning_enabled value mismatch for Bridge Domain"
                    " in agent, actual: %s, expected: %s" % (
                    bd['learning_enabled'], self.mac_learning_enabled))
                result = False
                return result

            #Uncomment BD name check, when bug 1665253 is fixed
            if bd['name'] != self.fq_name_str:
                self.logger.warn("Name mismatch for Bridge Domain"
                    " in agent, actual: %s, expected: %s" % (
                    bd['name'], self.bd_name))
                result = False
                return result

            self.logger.info("Verifications in Agent %s for BD %s for VN info"
                " passed" %(vmi_host_ip, self.bd_name))

        return True
    #end verify_bd_for_vn_in_agent

    @retry(delay=2, tries=2)
    def verify_bd_for_vmi_in_computes(self, vmi_uuid):
        '''
        Verify BD details in VMI in computes:
            Verify in agent as well as vrouter
        '''
        if vmi_uuid:
            vmi_host = self.vnc_h.get_vmi_host_name(vmi_uuid)
            if not vmi_host:
                self.logger.warn("VMI %s host could not be found from VNC API" % (
                    vmi_uuid))
                return False
            vmi_host_ip = self.inputs.compute_info[vmi_host]
            vmis_in_agent = self.agent_inspect[vmi_host_ip].get_vna_tap_interface_by_vmi(vmi_uuid)

            if not vmis_in_agent:
                self.logger.warn("VMI %s is not found in Agent %s" % (
                    vmi_uuid, vmi_host_ip))
                return False
            vmi_in_agent = vmis_in_agent[0]
            if not vmi_in_agent['bridge_domain_list']:
                self.logger.warn("Bridge Domain for VMI %s is not found in Agent %s" % (
                    vmi_uuid, vmi_host_ip))
                return False

            bd_uuid_in_vmi = vmi_in_agent['bridge_domain_list'][0]['bridge_domain_uuid']
            #Verify bd uuid in agent
            if (self.bd_uuid != bd_uuid_in_vmi):
                self.logger.warn("Bridge Domain uuid mismatch"
                    " in agent, actual: %s, expected: %s" % (
                    bd_uuid_in_vmi, self.bd_uuid))
                result = False
                return result
            else:
                self.logger.info("Verification for Bridge Domain uuid %s for "
                    "VMI %s passed in agent %s" % (
                    bd_uuid_in_vmi, vmi_uuid, vmi_host_ip))

            #Vrouter verifications
            #Interface verification
            vmi_in_vrouter = self.agent_inspect[
                vmi_host_ip].get_vrouter_interfaces_by_name(vmi_in_agent['name'])
            #[TBD]Verify ISID and Bmac value here

            #[TBD]Route table verification
        return True
    #end verify_bd_for_vmi_in_computes

    @retry(delay=2, tries=2)
    def verify_bd_not_in_agent(self):
        """ Verify Bridge Domain not present in agent after BD is deleted.
        """

        for ip in self.inputs.compute_ips:
            bd_in_agent = self.agent_inspect[ip].get_bd(self.bd_uuid)
            if bd_in_agent:
                self.logger.warn("Bridge Domain %s is still seen in Agent %s as %s" % (
                    self.bd_name, ip, bd_in_agent))
                return False

            self.logger.info("Bridge Domain %s is removed from Agent %s" % (
                self.bd_name, ip))

        return True
    #end verify_bd_not_in_agent

    def verify_cleared_from_setup(self, verify=True):
        '''
            Verify that Bridge Domain is deleted from the setup
        '''
        if verify:
            assert self.verify_bd_not_in_agent(), ("BD cleanup verification "
                                                     "failed in agent")

