import os
import fixtures
from vnc_api.vnc_api import *
import uuid
import fixtures
from vnc_api_test import *
from contrail_fixtures import *
from common.connections import ContrailConnections
from tcutils.util import retry,get_plain_uuid
from time import sleep
from openstack import OpenstackAuth
from vcenter import VcenterAuth


class DomainFixture(fixtures.Fixture):

    def __init__(self,connections, auth=None, domain_name=None,
                 username=None, password=None, role='admin',
                 uuid=None):
        self.inputs = connections.inputs
        self.vnc_lib_h = connections.get_vnc_lib_h()
        self.logger = connections.logger
        self.connections = connections
        self.auth = connections.auth
        self.domain_name = domain_name
        self.uuid = uuid
        self.domain_obj = None
        self.already_present = False
        self.domain_fq_name = self.domain_name
        self.username = username
        self.password = password
        self.role = role
        self.domain_connections = None
        self.api_server_inspect = self.connections.api_server_inspect
        self.verify_is_run = False
        if not self.auth:
            if self.inputs.orchestrator == 'openstack':
                self.auth = OpenstackAuth(self.inputs.admin_username,
                              self.inputs.admin_password,
                              self.inputs.admin_domain, self.inputs, self.logger)
            else: # vcenter
                self.auth = VcenterAuth(self.inputs.admin_user,
                              self.inputs.admin_password,
                              self.inputs.admin_domain, self.inputs)
        self.domain_username = None
        self.domain_user_password = None
    # end __init__
    
    def read(self):
        try:
            self.logger.info('Reading existing Domain with UUID %s' % (
                                                        self.uuid))
            domain_obj = self.vnc_lib_h.domain_read(id=self.uuid)
        except NoIdError, e:
            self.logger.exception('UUID %s not found, unable to read Domain' % (
                self.uuid))
            raise e
        self._populate_attr(domain_obj)
        self.already_present = True
    # end read
    
    def _populate_attr(self, domain_obj):
        self.domain_obj = domain_obj
        self.domain_fq_name = domain_obj.fq_name
        self.domain_name = domain_obj.name
        self.uuid = domain_obj.uuid
    # end _populate_attr

    def _create_domain(self):
        self.uuid = self.auth.create_domain(self.domain_name)
        domain_obj = self.vnc_lib_h.domain_read(id=self.uuid)
        self.logger.info('Created Domain:%s, ID : %s ' % (self.domain_name,
                                                           self.uuid))
        self._populate_attr(domain_obj)
    # end _create_domain

    def _delete_domain(self):
        self.auth.delete_domain(domain_name=self.domain_name)
        self.logger.info('Deleted Domain: %s, ID : %s ' % (self.domain_name,
                                                            self.uuid))
    # end _delete_domain

    def setUp(self):
        super(DomainFixture, self).setUp()
        self.create()

    def create(self):
        self.uuid = self.uuid or self.auth.get_domain_id(self.domain_name)
        if self.uuid:
            self.read()
            self.logger.info(
                    'Using existing domain %s(%s)'%(
                    self.domain_fq_name, self.uuid))
        elif self.domain_name == self.inputs.admin_domain:
             raise Exception('Domain %s found not creating' % (self.domain_name))
        else:
            self.logger.info('Domain %s not found, creating it' % (
                self.domain_name))
            self._create_domain()

    def get_uuid(self):
        return self.uuid

    def get_fq_name(self):
        return self.domain_fq_name

    def getObj(self):
        return self.domain_obj

    def cleanUp(self):
        super(DomainFixture, self).cleanUp()
        self.delete()
        
    def update_domain(self,domain_name,description='',enabled=True):
        try:
            obj = self.auth.update_domain(domain_id=get_plain_uuid(self.uuid),domain_name=domain_name,
                                    description=description,enabled=enabled)
            slef.logger.info('Domain updated successfully %s',obj.name)
            self.read()
            return obj
        except:
            self.logger.info('Domain updation failed')
    
    def get_domain(self):
       return self.auth.get_domain(domain_id=get_plain_uuid(self.uuid)) 
       
    def get_domain_connections(self):
        self.dm_connections= ContrailConnections(self.inputs, self.logger,
            username=self.domain_username,
            password=self.domain_password,
            domain_name = self.domain_name,
            )
        self.vnc_lib= self.dm_connections.vnc_lib
        self.auth = self.dm_connections.auth
        
    def delete(self, verify=False):
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            if not self.check_no_domain_references():
                self.logger.warn('One or more references still present' 
                    ', will not delete the Domain %s' % (self.domain_name))
                return
            self._delete_domain()
            if self.verify_is_run or verify:
                assert self.verify_on_cleanup()
        else:
            self.logger.debug('Skipping the deletion of Domain %s' %
                              self.domain_fq_name)

    # end cleanUp

    @retry(delay=2, tries=30)
    def check_no_domain_references(self):
        vnc_domain_obj = self.vnc_lib_h.domain_read(id=self.uuid)
        prjs = vnc_domain_obj.get_projects()
        if prjs:
            self.logger.debug('Domain %s still has Projects %s before deletion' %(
                self.domain_name, prjs))
            return False
        svc_tmps = vnc_domain_obj.get_service_templates()
        if svc_tmps:
            self.logger.debug('Domain %s still has Service Templates %s before deletion' %(
                self.domain_name, svc_tmps))
            return False
        vdns = vnc_domain_obj.get_virtual_DNSs()
        if vdns:
            self.logger.debug('Domain %s still has vDNSs %s before deletion' %(
                self.domain_name, vdns))
            return False
        return True
    # end check_no_domain_references

    def verify_on_setup(self):
        result = True
        if not self.verify_domain_in_api_server():
            result &= False
            self.logger.error('Verification of domain %s in APIServer '
                              'failed!! ' % (self.domain_name))
        self.verify_is_run = True
        return result
    # end verify_on_setup

    @retry(delay=2, tries=6)
    def verify_domain_in_api_server(self):
        if self.inputs.orchestrator == 'vcenter':
            self.logger.debug('No need to verify domains in case of vcenter')
            return True
        result = True
        cs_domain_obj = self.api_s_inspect.get_cs_domain(
            self.domain_name)
        if not cs_domain_obj:
            self.logger.debug('Domain %s not found in API Server %s'
                             ' ' % (self.domain_name, api_s_inspect._ip))
            result &= False
            return result
        if cs_domain_obj['domain']['uuid'] != self.uuid:
            self.logger.warn('Domain id %s got from API Server is'
                             ' not matching expected ID %s' % (
                                 cs_domain_obj['domain']['uuid'], self.uuid))
            result &= False
        if result:
            self.logger.info('Verification of Domain %s in API Server %s'
                             ' passed ' % (self.domain_name, api_s_inspect._ip))
        return result
    # end verify_domain_in_api_server

    @retry(delay=2, tries=5)
    def verify_domain_not_in_api_server(self):
        if self.inputs.orchestrator == 'vcenter':
            self.logger.debug('No need to verify domains in case of vcenter')
            return True
        result = True
        cs_domain_obj = self.api_s_inspect.get_cs_domain(
            self.domain_name)
        self.logger.info("Check for Domain %s after deletion, got cs_domain_obj %s" %
            (self.domain_name, cs_domain_obj))
        if cs_domain_obj:
            self.logger.debug('Domain %s is still found in API Server %s'
                             'with ID %s ' % (self.domain_name, api_s_inspect._ip,
                                              cs_domain_obj['domain']['uuid']))
            result &= False
        if result:
            self.logger.info('Verification of Domain %s removal in API Server '
                             ' %s passed ' % (self.domain_name, api_s_inspect._ip))
        return result
    # end verify_domain_not_in_api_server

    @retry(delay=2, tries=10)
    def verify_on_cleanup(self):
        result = True
        if not self.verify_domain_not_in_api_server():
            result &= False
            self.logger.error('Domain %s is still present in API Server' % (
                self.domain_name))
        return result
    # end verify_on_cleanup

    def set_user_creds(self, username, password):
        '''Set a user,password who is allowed to login to this domain
        '''
        self.domain_username = username
        self.domain_user_password = password
    # end set_user_creds
# end ProjectFixture
