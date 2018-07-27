import os
import fixtures
import uuid
import fixtures

from common.connections import ContrailConnections
from tcutils.util import retry
from time import sleep
from tcutils.util import get_dashed_uuid

from common.openstack_libs import ks_exceptions

class UserFixture(fixtures.Fixture):

    def __init__(self, connections, username=None, password=None, tenant=None, role='admin'):
        self.inputs= connections.inputs
        self.connections= connections
        self.logger = self.inputs.logger
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter, However we satisfy the test infra
            # with dummy fixture objects
            return
        self.created = False
        self.username = username 
        self.password = password 
        self.tenant = tenant
        self.role = role
        self.email = str(username) + "@example.com"
        self.verify_is_run = False
        self.auth = connections.auth
    # end __init__

    def add_user_to_tenant(self, tenant, user, role):
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return
        self.auth.add_user_to_project(user, tenant, role)

    def remove_user_from_tenant(self, tenant, user, role):
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return
        self.auth.remove_user_from_project(user, role, tenant)

    def setUp(self):
        super(UserFixture, self).setUp()
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return
        if self.auth.get_user_id(self.username):
            return
        self.auth.create_user(self.username, self.password,
                              self.connections.project_name,
                              self.connections.orch_domain_name)
        self.created = True
        try:
            #if test tenant already created, associate user to tenant
            if self.tenant:
                self.add_user_to_tenant(self.tenant, self.username, self.role)
        except ks_exceptions.NotFound, e:
            self.logger.info('Project %s not found, skip adding user %s' % (
                self.tenant, self.username))
    # end setUp

    def cleanUp(self):
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if not self.created:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            self.logger.info('Deleting user %s' %self.username)
            self.auth.delete_user(self.username)
            if self.verify_is_run:
                assert self.verify_on_cleanup()            
        else:
            self.logger.debug('Skipping the deletion of User %s' %
                              self.username)
        super(UserFixture, self).cleanUp()
    # end cleanUp

    def verify_on_setup(self):
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return True
        result = True
        if not self.auth.get_user_id(self.username):
            result &= False
            self.logger.error('Verification of user %s in keystone '
                              'failed!! ' % (self.username))
        self.verify_is_run = True
        return result
    # end verify_on_setup

    def verify_on_cleanup(self):
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return True
        result = True
        if self.auth.get_user_id(self.username):
            result &= False
            self.logger.error('User %s is still present in Keystone' % (
                self.username))
        return result
    # end verify_on_cleanup
# end UserFixture
