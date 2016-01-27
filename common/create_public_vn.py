import project_test
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
import os
import fixtures
from test import BaseTestCase
import time
from floating_ip import *
from vn_test import *
from control_node import *
from common import isolated_creds
from tcutils.util import Singleton


class PublicVn(fixtures.Fixture):
    __metaclass__ = Singleton

    def __init__(self, user, password, inputs, ini_file = None ,logger = None, mx_rt = None):

#        self.project_name = project_name
        self.user_name = user
        self.password = password
        self.inputs = inputs
        self.ini_file = ini_file
        self.logger = logger
        self.public_vn = self.inputs.public_vn 
        self.public_tenant = self.inputs.public_tenant
        self.setUp()
        self.create_public_vn(mx_rt)
        self.create_floatingip_pool()
        self.configure_control_nodes()

    def setUp(self):
        super(PublicVn, self).setUp()
        self.isolated_creds = isolated_creds.IsolatedCreds(self.public_tenant, \
                self.inputs, ini_file = self.ini_file, \
                logger = self.logger,
                username=self.user_name,
                password=self.password)
        self.isolated_creds.setUp()
        self.project = self.isolated_creds.create_tenant()
        self.isolated_creds.create_and_attach_user_to_tenant()
        self.inputs = self.isolated_creds.get_inputs()
        self.connections = self.isolated_creds.get_conections()
        self.isolated_creds.create_and_attach_user_to_tenant(self.user_name,self.password)
        self.project.set_sec_group_for_allow_all(\
                 self.public_tenant, 'default')

    def create_public_vn(self,mx_rt = None):
        if (('MX_GW_TEST' in os.environ) and (
                os.environ.get('MX_GW_TEST') == '1')):
            fip_pool_name = self.inputs.fip_pool_name
            fvn_name = self.public_vn
            fip_subnets = [self.inputs.fip_pool]
            if not mx_rt:
                mx_rt = self.inputs.mx_rt
            self.public_vn_fixture = self.useFixture(
                VNFixture(
                    project_name=self.project.project_name,
                    connections=self.connections,
                    vn_name=fvn_name,
                    inputs=self.inputs,
                    subnets=fip_subnets,
                    router_asn=self.inputs.router_asn,
                    rt_number=mx_rt,
                    router_external=True))
            assert self.public_vn_fixture.verify_on_setup()
            self.logger.info('created public VN:%s' % fvn_name)
    # end createPublicVN

    def create_floatingip_pool(self):
        if (('MX_GW_TEST' in os.environ) and (
                os.environ.get('MX_GW_TEST') == '1')):
            fip_pool_name = self.inputs.fip_pool_name
            fvn_name = self.public_vn
            fip_subnets = [self.inputs.fip_pool]
            self.fip_fixture = self.useFixture(
                FloatingIPFixture(
                   project_name=self.public_tenant,
                   inputs=self.inputs,
                   connections=self.connections,
                   pool_name=fip_pool_name,
                   vn_id=self.public_vn_fixture.vn_id,
                   option='neutron',
                   vn_name=fvn_name))
            assert self.fip_fixture.verify_on_setup()
            self.logger.info('created FIP Pool:%s under Project:%s' %
                                (self.fip_fixture.pool_name,
                                 self.project.project_name))
    # end createfloatingip

    def configure_control_nodes(self):

        # Configuring all control nodes here
        if (('MX_GW_TEST' in os.environ) and (
                os.environ.get('MX_GW_TEST') == '1')):
            router_name = self.inputs.ext_routers[0][0]
            router_ip = self.inputs.ext_routers[0][1]
            for entry in self.inputs.bgp_ips:
                hostname = self.inputs.host_data[entry]['name']
                entry_control_ip = self.inputs.host_data[
                    entry]['host_control_ip']
                cn_fixture1 = self.useFixture(
                    CNFixture(
                        connections=self.connections,
                        router_name=hostname,
                        router_ip=entry_control_ip,
                        router_type='contrail',
                        inputs=self.inputs))
            cn_fixturemx = self.useFixture(
                CNFixture(
                    connections=self.connections,
                    router_name=router_name,
                    router_ip=router_ip,
                    router_type='mx',
                    inputs=self.inputs))
            sleep(10)
            assert cn_fixturemx.verify_on_setup()
            # TODO Configure MX. Doing Manually For Now

