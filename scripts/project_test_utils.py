''' This module provides utils for Project tests '''
import os
import inspect
import copy
import fixtures
from topo_helper import topology_helper
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from contrail_test_init import *
from connections import ContrailConnections
from keystoneclient.v2_0 import client as ksclient


def _create_project_return_connection(self, projectname):
    '''
    Create specified project with non-admin user
    '''
    password = 'contrail123'
    username = 'user-' + projectname
    role = 'admin'
    user_list = [(username, password, role)]
    if projectname == 'admin':
        self.logger.info('Project admin already exist, no need to create')
        return [self.inputs, self.connections]
    auth_url = 'http://%s:5000/v2.0' % (self.inputs.cfgm_ip)
    auth_url = os.getenv('OS_AUTH_URL') or \
                   'http://' + self.inputs.openstack_ip + ':5000/v2.0'
    kc = ksclient.Client(
        username=self.inputs.stack_user, password=self.inputs.stack_password,
        tenant_name=self.inputs.project_name, auth_url=auth_url)

    project_list_in_api_before_test = self.vnc_lib.projects_list()
    print project_list_in_api_before_test
    if projectname in str(project_list_in_api_before_test):
        self.logger.info('Project already present. Cleaning them')
        self.vnc_lib.project_delete(fq_name=["default-domain", projectname])
        time.sleep(10)
    else:
        self.logger.info('Proceed with creation of new project.')

    user_pass = dict((n, p) for (n, p, r) in user_list)
    user_role = dict((n, r) for (n, p, r) in user_list)
    user_set = set([n for (n, p, r) in user_list])
    role_set = set([r for (n, p, r) in user_list])

    users = set([user.name for user in kc.users.list()])
    roles = set([user.name for user in kc.roles.list()])
    tenants = kc.tenants.list()
    admin_tenant = [x for x in tenants if x.name == 'admin'][0]

    create_user_set = user_set - users
    create_role_set = role_set - roles
    for new_tenant in [projectname]:
        kc.tenants.create(new_tenant)
        self.logger.info('Created Project:%s ' % (new_tenant))
        role_dict = dict((role.name, role) for role in kc.roles.list())
    tenant_dict = dict((tenant.name, tenant) for tenant in kc.tenants.list())

    for name in create_user_set:
        user = kc.users.create(
            name, user_pass[name], '', tenant_id=admin_tenant.id)
        self.logger.info('Created User:%s with Role:%s for Project:%s ' %
                         (name, user_role[name], new_tenant))
        for new_tenant in [projectname]:
            kc.roles.add_user_role(
                user, role_dict[user_role[name]], tenant_dict[new_tenant])

    user_dict = dict((user.name, user) for user in kc.users.list())

    # Projects
    self.new_proj_inputs = self.useFixture(
        ContrailTestInit(self.ini_file, stack_user=user_list[0][0],
                         stack_password=user_list[0][1], project_fq_name=['default-domain', projectname]))
    self.new_proj_connections = ContrailConnections(self.new_proj_inputs)

    # cleanup non-default projects and users at the end of test
    for new_tenant in [projectname]:
        self.addCleanup(kc.tenants.delete, tenant_dict[new_tenant])
    for name in create_user_set:
        self.addCleanup(kc.users.delete, user_dict[name])

    return [self.new_proj_inputs, self.new_proj_connections]

if __name__ == '__main__':
    ''' Unit test to invoke project utils.. '''

# end __main__
