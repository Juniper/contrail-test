import time
import test
from common.connections import ContrailConnections
from common import isolated_creds
from vn_test import VNFixture
from heat_test import HeatFixture
from vm_test import VMFixture
from project_test import ProjectFixture
from tcutils.util import get_random_name, retry
from fabric.context_managers import settings
from fabric.api import run
from fabric.operations import get, put
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
import template as template
import env as env
import ConfigParser
import re

contrail_api_conf = '/etc/contrail/contrail-api.conf'


class BaseHeatTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseHeatTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(
            cls.__name__,
            cls.inputs,
            ini_file=cls.ini_file,
            logger=cls.logger)
        cls.admin_connections = cls.isolated_creds.get_admin_connections()
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant()
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections()
        cls.admin_inputs = cls.isolated_creds.get_admin_inputs()
        cls.admin_connections = cls.isolated_creds.get_admin_connections()
        cls.quantum_fixture = cls.connections.quantum_fixture
        cls.nova_fixture = cls.connections.nova_fixture
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.isolated_creds.delete_tenant()
        super(BaseHeatTest, cls).tearDownClass()
    # end tearDownClass

    def get_stack_obj(self):
        return self.useFixture(
            HeatFixture(connections=self.connections, username=self.inputs.username, password=self.inputs.password,
                        project_fq_name=self.inputs.project_fq_name, 
                        inputs=self.inputs, cfgm_ip=self.inputs.cfgm_ip, openstack_ip=self.inputs.openstack_ip))
    # end get_stack_obj

    def get_template(self, template_name):
        template_name = '%s' % template_name
        return getattr(template, template_name)
    # end get_template

    def get_env(self, env_name):
        env_name = '%s' % env_name
        return getattr(env, env_name)
    # end get_env

    def verify_vn(self, stack, env):
        result = False
        stack.get()
        time.sleep(5)
        for output in stack.to_dict()['outputs']:
            if output['output_key'] == 'right_net_id':
                vn_id = output['output_value']
                vn_obj = self.vnc_lib.virtual_network_read(id=vn_id)
                vn_name = str(env['parameters']['right_net_name'])
                subnet = str(env['parameters']['right_net_cidr'])
            elif output['output_key'] == 'left_net_id':
                vn_id = output['output_value']
                vn_obj = self.vnc_lib.virtual_network_read(id=vn_id)
                vn_name = str(env['parameters']['left_net_name'])
                subnet = str(env['parameters']['left_net_cidr'])
        vn_fix = self.useFixture(VNFixture(project_name=self.inputs.project_name,
                                           vn_name=vn_name, inputs=self.inputs, subnets=[subnet], connections=self.connections))
        if vn_fix.vn_id == vn_id:
            self.logger.info('VN %s launched successfully' % vn_name)
        assert vn_fix.verify_on_setup()
        return vn_fix
    # end verify_vn
