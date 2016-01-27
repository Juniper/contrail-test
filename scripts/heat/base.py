import time
import test
from common.connections import ContrailConnections
from common import isolated_creds
from vn_test import VNFixture
from heat_test import *
from vm_test import VMFixture
from svc_template_fixture import *
from svc_instance_fixture import *
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
import copy

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
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
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

    def get_template(self, template_name):
        template_name = '%s' % template_name
        return getattr(template, template_name)
    # end get_template

    def get_env(self, env_name):
        env_name = '%s' % env_name
        return copy.deepcopy(getattr(env, env_name))
    # end get_env

    def verify_vn(self, stack, env, stack_name):
        op = stack.stacks.get(stack_name).outputs
        time.sleep(5)
        for output in op:
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
            elif output['output_key'] == 'transit_net_id':
                vn_id = output['output_value']
                vn_obj = self.vnc_lib.virtual_network_read(id=vn_id)
                vn_name = str(env['parameters']['transit_net_name'])
                subnet = str(env['parameters']['transit_net_cidr'])
        vn_fix = self.useFixture(VNFixture(project_name=self.inputs.project_name,
                                           vn_name=vn_name, inputs=self.inputs, subnets=[subnet], connections=self.connections))
        if vn_fix.vn_id == vn_id:
            self.logger.info('VN %s launched successfully via heat' % vn_name)
        assert vn_fix.verify_on_setup()
        return vn_fix
    # end verify_vn

    def update_stack(self, hs_obj, stack_name=None, change_set=[]):
        template = self.get_template(template_name=stack_name + '_template')
        env = self.get_env(env_name=stack_name + '_env')
        parameters = env['parameters']
        if env['parameters'][change_set[0]] != change_set[1]:
            parameters[change_set[0]] = change_set[1]
            hs_obj.update(stack_name, parameters)
        else:
            self.logger.info(
                'No change seen in the Stack %s to update' % stack_name)
    # end update_stack

    def config_vn(self, stack_name=None):
        template = self.get_template(template_name=stack_name + '_template')
        env = self.get_env(env_name=stack_name + '_env')
        vn_hs_obj = self.config_heat_obj(stack_name, template, env)
        stack = vn_hs_obj.heat_client_obj
        vn_fix = self.verify_vn(stack, env, stack_name)
        self.logger.info(
            'VN %s launched successfully with ID %s' % (vn_fix.vn_name, vn_fix.vn_id))
        return vn_fix, vn_hs_obj
    # end config_vn

    def config_heat_obj(self, stack_name, template, env):
        return self.useFixture(HeatStackFixture(connections=self.connections,
                                                inputs=self.inputs, stack_name=stack_name, project_fq_name=self.inputs.project_fq_name, template=template, env=env))
    # end config_heat_obj

    def config_vms(self, vn_list):
        stack_name = 'vms'
        template = self.get_template(template_name='vms_template')
        env = self.get_env(env_name='vms_env')
        env['parameters']['right_net_id'] = vn_list[1].vn_id
        env['parameters']['left_net_id'] = vn_list[0].vn_id
        vms_hs_obj = self.config_heat_obj(stack_name, template, env)
        stack = vms_hs_obj.heat_client_obj
        vm_fix = self.verify_vms(stack, vn_list, stack_name)
        return vm_fix

    def verify_vms(self, stack, vn_list, stack_name):
        op = stack.stacks.get(stack_name).outputs
        time.sleep(5)
        vm1_fix = self.useFixture(VMFixture(project_name=self.inputs.project_name,
                                            vn_obj=vn_list[0].obj, vm_name='left_vm', connections=self.connections))
        vm2_fix = self.useFixture(VMFixture(project_name=self.inputs.project_name,
                                            vn_obj=vn_list[1].obj, vm_name='right_vm', connections=self.connections))
        assert vm1_fix.wait_till_vm_is_up()
        assert vm2_fix.wait_till_vm_is_up()
        for output in op:
            if output['output_value'] == vm1_fix.vm_ip:
                self.logger.info(
                    'VM %s launched successfully' % vm1_fix.vm_name)
            elif output['output_value'] == vm2_fix.vm_ip:
                self.logger.info(
                    'VM %s launched successfully' % vm2_fix.vm_name)
        vms_list = [vm1_fix, vm2_fix]
        return vms_list
    # end verify_vn

    def config_svc_template(self, stack_name=None, scaling=False, mode='in-network-nat'):
        template = self.get_template(template_name='svc_temp_template')
        env = self.get_env(env_name='svc_temp_env')
        env['parameters']['mode'] = mode
        env['parameters']['name'] = stack_name
        if mode == 'transparent':
            env['parameters']['image'] = 'vsrx-bridge'
        if mode == 'in-network':
            env['parameters']['image'] = 'vsrx-fw'
        if scaling:
            env['parameters']['service_scaling'] = "True"
            if mode != 'in-network-nat':
                env['parameters']['shared_ip_list'] = 'False,True,True'
            else:
                env['parameters']['shared_ip_list'] = 'False,True,False'
        svc_temp_hs_obj = self.config_heat_obj(stack_name, template, env)
        st = self.verify_st(stack_name, env, scaling)
        return st
    # end config_svc_template

    def verify_st(self, stack_name, env, scaling):
        st_name = env['parameters']['name']
        svc_img_name = env['parameters']['image']
        svc_type = env['parameters']['type']
        if_list = env['parameters']['service_interface_type_list']
        svc_mode = env['parameters']['mode']
        svc_scaling = scaling
        flavor = env['parameters']['flavor']
        st_fix = self.useFixture(SvcTemplateFixture(
            connections=self.connections, inputs=self.inputs, domain_name='default-domain',
            st_name=st_name, svc_img_name=svc_img_name, svc_type=svc_type,
            if_list=if_list, svc_mode=svc_mode, svc_scaling=svc_scaling, flavor=flavor, ordered_interfaces=True))
        assert st_fix.verify_on_setup()
        return st_fix
    # end verify_st

    def config_svc_instance(self, stack_name, st_fq_name, st_obj, vn_list, max_inst='1', svc_mode='in-network-nat'):
        template = self.get_template(template_name='svc_inst_template')
        env = self.get_env(env_name='svc_inst_env')
        env['parameters']['service_template_fq_name'] = st_fq_name
        if svc_mode != 'transparent':
            env['parameters']['right_net_id'] = vn_list[1].vn_id
            env['parameters']['left_net_id'] = vn_list[0].vn_id
        else:
            env['parameters']['right_net_id'] = 'auto'
            env['parameters']['left_net_id'] = 'auto'
        env['parameters'][
            'service_instance_name'] = get_random_name('svc_inst')
        env['parameters']['max_instances'] = max_inst
        si_hs_obj = self.config_heat_obj(stack_name, template, env)
        si_name = env['parameters']['service_instance_name']
        si_fix = self.verify_si(si_name, st_obj, max_inst, svc_mode)
        si_fix.verify_on_setup()
        return si_fix, si_hs_obj

        # end config_svc_instance

    @retry(delay=2, tries=5)
    def verify_svm_count(self, hs_obj, stack_name, svm_count):
        result = True
        stack = hs_obj.heat_client_obj
        op = stack.stacks.get(stack_name).outputs
        for output in op:
            if output['output_key'] == u'num_active_service_instance_vms':
                if int(output['output_value']) != int(svm_count):
                    self.logger.error('SVM Count mismatch')
                    result = False
                else:
                    self.logger.info(
                        'There are %s Active SVMs in the SI' % output['output_value'])
            if output['output_key'] == u'service_instance_vms':
                self.logger.info('%s' % output['output_value'])
        return result
    # end get_svms

    def verify_si(self, si_name, st_obj, max_inst, svc_mode):
        if max_inst > 1:
            if svc_mode != 'in-network-nat':
                if_list = [['management', False, False],
                           ['left', True, False], ['right', True, False]]
            else:
                if_list = [['management', False, False],
                           ['left', True, False], ['right', False, False]]
        else:
            if_list = [['management', False, False],
                       ['left', False, False], ['right', False, False]]
        svc_inst = self.useFixture(SvcInstanceFixture(
            connections=self.connections, inputs=self.inputs,
            domain_name='default-domain', project_name=self.inputs.project_name, si_name=si_name,
            svc_template=st_obj, if_list=if_list))
        assert svc_inst.verify_on_setup()
        return svc_inst

    # end verify_si

    def config_svc_chain(self, si_fq_name, vn_list, stack_name='svc_chain'):
        template = self.get_template(template_name='svc_chain_template')
        env = self.get_env(env_name='svc_chain_env')
        env['parameters']['apply_service'] = si_fq_name
        env['parameters']['dst_vn_id'] = vn_list[1].vn_id
        env['parameters']['src_vn_id'] = vn_list[0].vn_id
        env['parameters']['policy_name'] = get_random_name('svc_chain')
        svc_hs_obj = self.config_heat_obj(stack_name, template, env)
        return svc_hs_obj
    # end config_svc_chain
