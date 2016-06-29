from common.isolated_creds import *
from test import BaseTestCase
import time

class BaseTestCase_v1(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = None
        cls.admin_inputs = None
        cls.admin_connections = None
        super(BaseTestCase_v1, cls).setUpClass()

        if not cls.inputs.tenant_isolation:
            project_name = cls.inputs.stack_tenant
        else:
            project_name = cls.__name__

        cls.isolated_creds = IsolatedCreds(
            cls.inputs,
            project_name=project_name,
            ini_file=cls.ini_file,
            logger=cls.logger)

        if cls.inputs.tenant_isolation:
            cls.admin_isolated_creds = AdminIsolatedCreds(
                cls.inputs,
                ini_file=cls.ini_file,
                logger=cls.logger)
            cls.admin_isolated_creds.setUp()

            cls.project = cls.admin_isolated_creds.create_tenant(
                cls.isolated_creds.project_name)
            cls.admin_inputs = cls.admin_isolated_creds.get_inputs(cls.project)
            cls.admin_isolated_creds.create_and_attach_user_to_tenant(
                cls.project,
                cls.isolated_creds.username,
                cls.isolated_creds.password)
            cls.admin_connections = cls.admin_isolated_creds.get_connections(
                cls.admin_inputs)
        # endif

        cls.isolated_creds.setUp()
        if not cls.project:
            cls.project = cls.isolated_creds.create_tenant(
                cls.isolated_creds.project_name)
        cls.inputs = cls.isolated_creds.get_inputs(cls.project)
        cls.connections = cls.isolated_creds.get_connections(cls.inputs)
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if cls.inputs.tenant_isolation:
            cls.admin_isolated_creds.delete_tenant(cls.project)
            cls.admin_isolated_creds.delete_user(cls.isolated_creds.username)
        super(BaseTestCase_v1, cls).tearDownClass()
    # end tearDownClass

    def sleep(self, value):
        self.logger.debug('Sleeping for %s seconds..' % (value))
        time.sleep(value)
    # end sleep
        

