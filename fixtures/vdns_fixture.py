import fixtures
from vnc_api.vnc_api import *
from vnc_api.gen.cfixture import ContrailFixture
from vnc_api.gen.resource_test import VirtualDnsRecordTestFixtureGen

from tcutils.util import retry


class VdnsFixture(fixtures.Fixture):

    def __init__(self, inputs=None, connections=None, vdns_name=None,
                 dns_data=None, dns_domain_name='juniper.net', 
                 ttl=100, record_order='random', uuid=None):
        self.vnc_lib = connections.get_vnc_lib_h()
        self.api_s_inspect = connections.api_server_inspect
        self.cn_inspect = connections.cn_inspect
        self.inputs = connections.inputs
        self.logger = connections.logger
        self.connections = connections
        self.dns_domain_name = dns_domain_name
        self.ttl = ttl
        self.record_order = record_order
        self.vdns_name = vdns_name
        self.dns_data = dns_data
        self.uuid = uuid
        self.parent_type = 'domain'
        self.fq_name = [self.inputs.domain_name, self.vdns_name]
        self.verify_is_run = False
        self.obj = None
        self.already_present = True

    def read(self):
        if self.uuid:
            self.obj = self.vnc_lib.virtual_DNS_read(id = self.uuid)
            self.vdns_name = self.obj.name
            self.fq_name = self.obj.get_fq_name()

    def setUp(self):
        super(VdnsFixture, self).setUp()
        self.create()

    def create(self):
        try:
            self.uuid = self.uuid or self.vnc_lib.virtual_DNS_read(
                                         fq_name=self.fq_name).uuid
            self.read()
            self.logger.debug("vDNS: %s(%s) already present not creating" %
                             (self.vdns_name, self.uuid))
        except NoIdError:
            self.already_present = False
            self.logger.debug("Creating VDNS : %s", self.vdns_name)
            vdns_data = self.dns_data or self.get_vdns_data()
            vdns_obj = VirtualDns(self.vdns_name, virtual_DNS_data=vdns_data,
                                  parent_type=self.parent_type,
                                  fq_name=self.fq_name)
            self.uuid = self.vnc_lib.virtual_DNS_create(vdns_obj)
            self.obj = self.vnc_lib.virtual_DNS_read(id = self.uuid)

    def get_vdns_data(self):
        return VirtualDnsType(domain_name=self.dns_domain_name,
                              dynamic_records_from_client=True,
                              default_ttl_seconds=self.ttl,
                              record_order=self.record_order)

    def get_uuid(self):
        return self.uuid

    def get_obj(self):
        return self.obj

    def get_fq_name(self):
        return self.fq_name

    @property
    def vdns_fq_name(self):
         return ':'.join(self.get_fq_name())

    def cleanUp(self):
        super(VdnsFixture, self).cleanUp()
        self.delete()

    def delete(self, verify=False):
        if not self.already_present:
            self.logger.debug("Deleting VDNS Entry: %s", self.vdns_name)
            self.vnc_lib.virtual_DNS_delete(id = self.uuid)
            if self.verify_is_run or verify:
                result, msg = self.verify_on_cleanup()
                assert result, msg

    def verify_on_setup(self):
        retval = True
        errmsg = ''
        try:
            vdns = self.vnc_lib.virtual_DNS_read(fq_name=self.fq_name)
            self.logger.debug("VDNS: %s created succesfully", self.fq_name)
        except NoIdError:
            errmsg = errmsg + \
                "\n VDNS: %s not created." % self.vdns_fq_name
            self.logger.warn(errmsg)
            return False, errmsg
        self.logger.debug("Verify VDNS entry is shown in control node")
        retval1 = self.verify_vdns_in_control_node()
        if not retval1:
            retval = True and False
            errmsg = errmsg + "\n VDNS server " + \
                self.vdns_fq_name + \
                " info not found not found in control node"
            self.logger.error("VDNS info not found not found in control node")
        self.logger.debug("Verify VDNS entry is shown in the API server")
        retval2 = self.verify_vdns_in_api_server()
        if not retval2:
            retval = True and False
            errmsg = errmsg + "\n VDNS server " + \
                self.vdns_fq_name + \
                " info not found not found in API server"
            self.logger.error("VDNS info not found not found in API server")
        self.verify_is_run = True
        if not retval:
            return False, errmsg
        return True, None

    @retry(delay=3, tries=15)
    def verify_vdns_in_control_node(self):
        ''' verify VDNS data in control node'''
        result = True
        msg = ''
        for cn in self.inputs.bgp_ips:
            try:
                cn_s_dns = self.cn_inspect[cn].get_cn_vdns(
                    vdns=str(self.obj.name))
                if self.vdns_fq_name not in cn_s_dns['node_name']:
                    result = result and False
                    msg = msg + \
                        '\nvdns name info not matching with control name data'
                act_cn_vdns_data = cn_s_dns['obj_info'][
                    'data']['virtual-DNS-data']
                print act_cn_vdns_data
                exp_vdns_data = self.obj.get_virtual_DNS_data()
                if act_cn_vdns_data:
                    if exp_vdns_data.__dict__['domain_name'] != act_cn_vdns_data['domain-name']:
                        result = result and False
                        msg = msg + \
                            '\nvdns domain name is not matching with control node data'
                    if str(exp_vdns_data.__dict__['default_ttl_seconds']) != act_cn_vdns_data['default-ttl-seconds']:
                        result = result and False
                        msg = msg + \
                            '\nvdns ttl value is not matching with control node data'
                    if exp_vdns_data.__dict__['record_order'] != act_cn_vdns_data['record-order']:
                        result = result and False
                        msg = msg + \
                            '\nvdns record order value is not matching with control node data'
                    if exp_vdns_data.__dict__['next_virtual_DNS'] != act_cn_vdns_data['next-virtual-DNS']:
                        result = result and False
                        msg = msg + \
                            '\nvdns next virtual DNS data is not matching with control node data'
            except Exception as e:
                # Return false if we get an key error and for retry
                return False
        if msg != '':
            self.logger.info(
                "VDNS info is not matching with control node data\n %s:", msg)
        return result
    # end verify_dns_in_control_node

    @retry(delay=3, tries=5)
    def verify_vdns_in_api_server(self):
        ''' verify VDNS data in API server '''
        result = True
        api_s_dns = self.api_s_inspect.get_cs_dns(
            vdns_name=str(self.obj.name), refresh=True)
        print api_s_dns
        msg = ''
        try:
            if self.fq_name != api_s_dns['virtual-DNS']['fq_name']:
                result = result and False
                msg = msg + \
                    '\n fq name data is not matching with api server data'
            if self.obj.uuid != api_s_dns['virtual-DNS']['uuid']:
                result = result and False
                msg = msg + '\n UUID is is not matching with api server data'

            api_vdns_data = api_s_dns['virtual-DNS']['virtual_DNS_data']
            exp_vdns_data = self.obj.get_virtual_DNS_data()
            for data in api_vdns_data:
                if str(exp_vdns_data.__dict__[data]) != str(api_vdns_data.get(data)):
                    result = result and False
                    msg = msg + '\nvdns ' + data + \
                        ' is not matching with api server data'
        except Exception as e:
            # Return false if we get an key error and for retry
            return False

        if msg != '':
            self.logger.info(
                "VDNS info is not matching with API server\n %s:", msg)
        return result
    # end verify_vdns_in_api_server

    @retry(delay=2, tries=5)
    def verify_vdns_not_in_api_server(self):
        """Validate VDNS information in API-Server."""
        if self.api_s_inspect.get_cs_dns(vdns_name=str(self.obj.name), refresh=True) is not None:
            errmsg = "VDNS information %s still found in the API Server" % self.obj.name
            self.logger.warn(errmsg)
            return False
        else:
            self.logger.info(
                "VDNS information %s removed from the API Server", self.obj.name)
            return True

    @retry(delay=2, tries=25)
    def verify_vdns_not_in_control_node(self):
        for cn in self.inputs.bgp_ips:
            cn_s_dns = self.cn_inspect[cn].get_cn_vdns(
                vdns=str(self.obj.name))

            if cn_s_dns:
                errmsg = "VDNS information %s still found in the Control node" % self.obj.name
                self.logger.warn(errmsg)
                return False
            else:
                self.logger.info(
                    "VDNS information %s removed in the Control node", self.obj.name)
                return True

    def verify_on_cleanup(self):
        retval = True
        errmsg = ''
        try:
            vdns = self.vnc_lib.virtual_DNS_read(fq_name=self.fq_name)
            errmsg = errmsg + "VDNS info " + \
                self.fq_name + 'still not removed'
            self.logger.warn(errmsg)
            return False, errmsg
        except NoIdError:
            self.logger.info("VDNS info: %s deleted successfully." %
                             self.fq_name)
        status = self.verify_vdns_not_in_api_server()
        if not status:
            retval = retval and False
            errmsg = errmsg + "\nVdns info is not deleted from API Server"
        status = self.verify_vdns_not_in_control_node()
        if not status:
            retval = retval and False
            errmsg = errmsg + "\n VDNS info is not deleted from control node"
        if not retval:
            return False, errmsg
        return True, errmsg


class VdnsRecordFixture(fixtures.Fixture):

    def __init__(self, inputs=None, connections=None,
                 virtual_DNS_record_name=None, vdns_fqname=None,
                 virtual_DNS_record_data=None, uuid=None):
        self.vnc_lib = connections.get_vnc_lib_h()
        self.api_s_inspect = connections.api_server_inspect
        self.cn_inspect = connections.cn_inspect
        self.inputs = connections.inputs
        self.logger = connections.logger
        self.vdns_record_name = virtual_DNS_record_name
        self.vdns_record_data = virtual_DNS_record_data
        self.parent_fqname = vdns_fqname
        self.fq_name = self.parent_fqname + [self.vdns_record_name]
        self.uuid = uuid
        self.obj = None
        self.verify_is_run = False
        self.already_present = True

    def read(self):
        if self.uuid:
            self.obj = self.vnc_lib.virtual_DNS_record_read(id = self.uuid)
            self.vdns_record_name = self.obj.name
            self.fq_name = self.obj.get_fq_name()
            self.logger.debug("Fetched vdns Record Data: %s(%s)"%(
                              self.fq_name, self.uuid))

    def setUp(self):
        super(VdnsRecordFixture, self).setUp()
        self.create()

    def create(self):
        try:
            self.uuid = self.uuid or self.vnc_lib.virtual_DNS_record_read(
                                                fq_name=self.fq_name).uuid
            self.read()
        except NoIdError:
            self.already_present = False
            self.logger.debug("Creating VDNS record data : %s",
                              self.vdns_record_name)
            obj = VirtualDnsRecord(self.vdns_record_name,
                                  parent_type='virtual-DNS',
                                  fq_name=self.fq_name,
                                  virtual_DNS_record_data=self.vdns_record_data)
            self.uuid = self.vnc_lib.virtual_DNS_record_create(obj)
            self.obj = self.vnc_lib.virtual_DNS_record_read(id = self.uuid)

    @property
    def vdns_rec_fq_name(self):
        return ':'.join(self.fq_name)

    @property
    def vdns_name(self):
        return self.fq_name[:-1][-1]

    def cleanUp(self):
        super(VdnsRecordFixture, self).cleanUp()
        self.delete()

    def delete(self, verify=False):
        if not self.already_present:
            self.logger.debug("Deleting VDNS record data: %s",
                              self.vdns_record_name)
            self.vnc_lib.virtual_DNS_record_delete(id=self.uuid)
            if self.verify_is_run or verify:
                result, msg = self.verify_on_cleanup()
                assert result, msg

    def verify_on_setup(self):
        retval = True
        errmsg = ''
        self.logger.info("In verify_on_setup")
        self.verify_is_run = True
        try:
            vdns_rec = self.vnc_lib.virtual_DNS_record_read(
                fq_name=self.fq_name)
            self.logger.debug(
                "VDNS record: %s created succesfully", self.fq_name)
        except NoIdError:
            errmsg = errmsg + \
                "\n VDNS record: %s not created." % self.vdns_rec_fq_name
            self.logger.warn(errmsg)
            return False, errmsg

        self.logger.info("Verify VDNS record  is shown in the API server")
        ret_val1 = self.verify_vdns_rec_in_api_server()
        if not ret_val1:
            retval = True and False
            errmsg = errmsg + "\n VDNS record " + \
                self.vdns_rec_fq_name + \
                " is info not found in the control node\n"
            self.logger.error(
                "VDNS record info not found not found in control node")
        self.logger.info("Verify VDNS record  is shown in the control node")
        ret_val2 = self.verify_vdns_rec_in_cn_node()
        if not ret_val2:
            retval = True and False
            errmsg = errmsg + "\n VDNS record " + \
                self.vdns_rec_fq_name + \
                " is info not found in the control node\n"
            self.logger.error(
                "VDNS record info not found not found in the control node")

        return retval, errmsg
    # end of verify_on_setup

    def verify_on_cleanup(self):
        retval = True
        errmsg = ''
        try:
            vdns = self.vnc_lib.virtual_DNS_record_read(
                fq_name=self.vdns_rec_fq_name)
            errmsg = errmsg + 'VDNS record ' + \
                self.vdns_rec_fq_name + ' info still not removed'
            self.logger.warn(errmsg)
            return False, errmsg
        except NoIdError:
            self.logger.info(
                "VDNS record info: %s deleted successfully.", self.vdns_rec_fq_name)
        return retval, errmsg

        status = self.verify_vdns_rec_not_in_api_server()
        if not status:
            retval = retval and False
            errmsg = errmsg + \
                "\nVDNS record info is not deleted from API server"
        status = self.verify_vdns_rec_not_in_control_node()
        if not status:
            retval = retval and False
            errmsg = errmsg + \
                "\nVDNS record info is not deleted from control node"
        if not retval:
            return False, errmsg
        return True, errmsg
    # end of verify_on_cleanup

    @retry(delay=5, tries=5)
    def verify_vdns_rec_in_cn_node(self):
        ''' verify VDNS record data in API in Control node'''
        result = True
        msg = ''
        for cn in self.inputs.bgp_ips:
            try:
                cn_s_dns = self.cn_inspect[cn].get_cn_vdns_rec(
                    vdns=self.vdns_name, rec_name=self.vdns_record_name)
                if self.vdns_rec_fq_name not in cn_s_dns['node_name']:
                    result = result and False
                    msg = msg + \
                        '\nvdns name info not matching with control name data'
                act_cn_vdns_rec_data = cn_s_dns['obj_info'][
                    'data']['virtual-DNS-record-data']
                exp_vdns_rec_data = self.obj.get_virtual_DNS_record_data()
                if act_cn_vdns_rec_data:
                    if exp_vdns_rec_data.__dict__['record_name'] != act_cn_vdns_rec_data['record-name']:
                        result = result and False
                        msg = msg + \
                            '\nvdns record name is not matching with control node data'
                    if str(exp_vdns_rec_data.__dict__['record_ttl_seconds']) != act_cn_vdns_rec_data['record-ttl-seconds']:
                        result = result and False
                        msg = msg + \
                            '\nvdns record ttl value is not matching with control node data'
                    if exp_vdns_rec_data.__dict__['record_type'] != act_cn_vdns_rec_data['record-type']:
                        result = result and False
                        msg = msg + \
                            '\nvdns record type value is not matching with control node data'
                    if exp_vdns_rec_data.__dict__['record_data'] != act_cn_vdns_rec_data['record-data']:
                        result = result and False
                        msg = msg + \
                            '\nvdns record data is not matching with control node data'
            except Exception as e:
                # Return false if we get an key error and for retry
                return False
        if msg != '':
            self.logger.info(
                "VDNS record info is not matching with control node data\n %s:", msg)
        return result
    # end of  verify_vdns_rec_in_cn_node

    @retry(delay=5, tries=5)
    def verify_vdns_rec_in_api_server(self):
        ''' verify VDNS record data in API server '''
        result = True
        api_s_dns_rec = self.api_s_inspect.get_cs_dns_rec(
            rec_name=self.vdns_record_name, vdns_name=self.vdns_name, refresh=True)
        msg = ''
        try:
            if self.fq_name != api_s_dns_rec['virtual-DNS-record']['fq_name']:
                result = result and False
                msg = msg + \
                    '\n fq name data is not matching with DNS record data'
            if self.uuid != api_s_dns_rec['virtual-DNS-record']['uuid']:
                result = result and False
                msg = msg + '\n UUID is is not matching with DNS record data'

            api_vdns_rec_data = api_s_dns_rec[
                'virtual-DNS-record']['virtual_DNS_record_data']
            exp_vdns_rec_data = self.obj.get_virtual_DNS_record_data()
            for data in api_vdns_rec_data:
                if str(exp_vdns_rec_data.__dict__[data]) != str(api_vdns_rec_data.get(data)):
                    result = result and False
                    msg = msg + '\nvdns ' + data + \
                        ' is not matching with api server DNS record data'
        except Exception as e:
            # Return false if we get an key error and for retry
            return False
        if msg != '':
            self.logger.info(
                "VDNS record info is not matching with API Server data\n %s:", msg)
        return result
    # end of verify_vdns_rec_in_api_server

    @retry(delay=2, tries=5)
    def verify_vdns_rec_not_in_api_server(self):
        '''Validate VDNS record data not  in API-Server.'''
        if self.api_s_inspect.get_cs_dns_rec(rec_name=self.vdns_record_name, vdns_name=self.vdns_name, refresh=True) is not None:
            errmsg = "VDNS record information %s still found in the API Server" % self.vdns_record_name
            self.logger.warn(errmsg)
            return False
        else:
            self.logger.info(
                "VDNS record information %s removed from the API Server", self.vdns_record_name)
            return True

    @retry(delay=2, tries=5)
    def verify_vdns_rec_not_in_control_node(self):
        for cn in self.inputs.bgp_ips:
            cn_s_dns = self.cn_inspect[cn].get_cn_vdns_rec(vdns=self.vdns_name,
                                                rec_name=self.vdns_record_name)
            if cn_s_dns:
                errmsg = "VDNS record information %s still found in the"\
                         " Control node" % self.vdns_record_name
                self.logger.warn(errmsg)
                return False
            else:
                self.logger.info("VDNS record information %s removed in "
                                 " the Control node"%self.vdns_record_name)
                return True
